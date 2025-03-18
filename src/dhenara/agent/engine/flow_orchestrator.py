# Copyright 2024-2025 Dhenara Inc. All rights reserved.
# flow_orchestrator.py
#  from tenacity import retry, stop_after_attempt, wait_exponential : TODO Future
import asyncio
import json
import logging
from asyncio import Event, create_task
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from dhenara.agent.engine import NodeHandler, node_handler_registry
from dhenara.agent.engine.types import FlowContext, StreamingContext, StreamingStatusEnum
from dhenara.agent.resource.registry import resource_config_registry
from dhenara.agent.types import (
    ConditionalFlow,
    ExecutionStrategyEnum,
    FlowDefinition,
    FlowExecutionStatusEnum,
    FlowNode,
    FlowNodeExecutionResult,
    FlowNodeTypeEnum,
    FlowTypeEnum,
    LoopFlow,
    SwitchFlow,
)

# from common.csource.apps.model_apps.app_ai_connect.libs.tsg.orchestrator import AIModelCallOrchestrator
from dhenara.ai.types import (
    AIModelCallResponse,
)
from dhenara.ai.types.resource import ResourceConfig

from .execution_recorder import ExecutionRecorder

logger = logging.getLogger(__name__)


class FlowOrchestrator:
    def __init__(
        self,
        flow_definition: FlowDefinition,
        resource_config: ResourceConfig = None,
    ):
        self.flow_definition = flow_definition

        # Use provided resource_config or get from registry
        self.resource_config = resource_config or resource_config_registry.get("default")
        if not self.resource_config:
            raise ValueError("No resource configuration provided or found in registry")

        self.execution_recorder = None
        self._handler_instances = {}  # Cache for handler instances

    def get_node_execution_handler(self, flow_node_type: FlowNodeTypeEnum) -> NodeHandler:
        """Get or create a handler for the given node type."""
        if flow_node_type not in self._handler_instances:
            handler_class = node_handler_registry.get_handler(flow_node_type)
            self._handler_instances[flow_node_type] = handler_class()
        return self._handler_instances[flow_node_type]

    async def run(
        self,
        flow_context: FlowContext,
    ) -> dict[str, FlowNodeExecutionResult] | AIModelCallResponse:
        """Execute the flow with support for control flow."""
        try:
            flow_context.execution_status = FlowExecutionStatusEnum.RUNNING
            self.execution_recorder = ExecutionRecorder()
            await self.execution_recorder.update_execution_in_db(flow_context, create=True)

            # Handle different flow types
            flow_def = self.flow_definition

            if flow_def.flow_type == FlowTypeEnum.standard:
                # Standard flow with nodes

                if self.flow_definition.execution_strategy == ExecutionStrategyEnum.sequential:
                    result = await self._execute_sequential(flow_context)

                    # if self.has_any_streaming_node():
                    # if isinstance(result, AsyncGenerator):
                    if (
                        isinstance(result, AIModelCallResponse)
                        and result.stream_generator
                        and isinstance(result.stream_generator, AsyncGenerator)
                    ):
                        background_tasks = set()

                        # Create a background task to continue processing after streaming
                        task = create_task(self._continue_after_streaming(flow_context))
                        flow_context.execution_status = FlowExecutionStatusEnum.PENDING

                        # NOTE: Below 2 lines are from RUFF:RUF006
                        # https://docs.astral.sh/ruff/rules/asyncio-dangling-task/
                        # Add task to the set. This creates a strong reference.
                        background_tasks.add(task)

                        # To prevent keeping references to finished tasks forever,
                        # make each task remove its own reference from the set after completion:
                        task.add_done_callback(background_tasks.discard)

                        return result

                elif flow_def.execution_strategy == ExecutionStrategyEnum.parallel:
                    result = await self._execute_parallel(flow_context)
                else:
                    raise NotImplementedError(f"Unsupported execution strategy: {flow_def.execution_strategy}")

            elif flow_def.flow_type == FlowTypeEnum.condition:
                result = await self._execute_conditional_flow(flow_context, flow_def)

            elif flow_def.flow_type == FlowTypeEnum.loop:
                result = await self._execute_loop_flow(flow_context, flow_def)

            elif flow_def.flow_type == FlowTypeEnum.switch:
                result = await self._execute_switch_flow(flow_context, flow_def)

            else:
                raise NotImplementedError(f"Unsupported flow type: {flow_def.flow_type}")

            # completion logic
            flow_context.execution_status = FlowExecutionStatusEnum.COMPLETED
            logger.debug(f"execute: Execution completed. execution_results={flow_context.execution_results}")

            await self.execution_recorder.update_execution_in_db(flow_context)
            logger.debug("execute: Finished updating DB")
            return flow_context.execution_results

        except Exception:
            flow_context.execution_status = FlowExecutionStatusEnum.FAILED
            logger.exception("Flow execution failed")
            raise

    async def _execute_conditional_flow(
        self, flow_context: FlowContext, flow_def: ConditionalFlow
    ) -> dict[str, FlowNodeExecutionResult]:
        """Execute a conditional flow."""
        # Update evaluation context
        flow_context.update_evaluation_context()

        # Evaluate condition
        try:
            condition_result = flow_context.evaluation_context.evaluate(flow_def.condition_expr)

            # Determine which branch to execute
            branch = flow_def.true_branch if condition_result else flow_def.false_branch

            if not branch:
                # No branch to execute
                logger.info(f"Condition evaluated to {condition_result}, but no applicable branch exists")
                return {}

            # Create sub-orchestrator for the branch
            sub_orchestrator = FlowOrchestrator(flow_definition=branch, resource_config=self.resource_config)

            # Execute the branch
            # Mark which branch we're executing in the path
            branch_name = "true_branch" if condition_result else "false_branch"
            flow_context.push_subflow(branch_name)

            try:
                await sub_orchestrator.run(flow_context)
            finally:
                flow_context.pop_subflow()

            # Return execution results
            return flow_context.execution_results

        except Exception as e:
            logger.exception(f"Error in conditional flow: {e}")
            flow_context.execution_status = FlowExecutionStatusEnum.FAILED
            flow_context.execution_failed = True
            flow_context.execution_failed_message = f"Conditional flow execution failed: {e}"
            return {}

    async def _execute_loop_flow(
        self, flow_context: FlowContext, flow_def: LoopFlow
    ) -> dict[str, FlowNodeExecutionResult]:
        """Execute a loop flow."""
        # Initialize loop state
        loop_id = f"loop_{id(flow_def)}"
        loop_state = flow_context.start_loop(loop_id)

        # Create sub-orchestrator for the loop body
        body_orchestrator = FlowOrchestrator(flow_definition=flow_def.body, resource_config=self.resource_config)

        try:
            if flow_def.loop_type == "for":
                # For loop - evaluate items expression
                flow_context.update_evaluation_context()
                items = flow_context.evaluation_context.evaluate(flow_def.items_expr)

                # Iterate over items
                for i, item in enumerate(items):
                    if flow_def.max_iterations and i >= flow_def.max_iterations:
                        logger.warning(f"Loop reached max iterations ({flow_def.max_iterations})")
                        break

                    # Update loop state
                    loop_state.iteration = i
                    loop_state.item = item

                    # Update evaluation context with loop variables
                    flow_context.evaluation_context.variables[flow_def.iteration_var] = i
                    if flow_def.item_var:
                        flow_context.evaluation_context.variables[flow_def.item_var] = item

                    # Execute the loop body
                    flow_context.push_subflow(f"{loop_id}_iteration_{i}")
                    try:
                        await body_orchestrator.run(flow_context)

                        # Capture results if requested
                        if flow_def.capture_results:
                            # Get results for this iteration
                            iteration_results = {}
                            for node_id, result in flow_context.execution_results.items():
                                # Only include results from the current iteration path
                                if node_id.startswith(flow_context.get_current_subflow_id()):
                                    iteration_results[node_id] = result  # noqa: PERF403 : TODO_FUTURE

                            loop_state.iteration_results.append(iteration_results)

                        # Store context if pass_state is enabled
                        if flow_def.pass_state:
                            # Save current context state to pass to next iteration
                            loop_state.context = {
                                key: value
                                for key, value in flow_context.evaluation_context.variables.items()
                                if key not in ["iteration", "item"]  # Don't include loop control variables
                            }
                    finally:
                        flow_context.pop_subflow()

                    # Check for execution failure
                    if flow_context.execution_failed:
                        break

            elif flow_def.loop_type == "while":
                # While loop - continue until condition is false
                i = 0
                while True:
                    # Check max iterations
                    if flow_def.max_iterations and i >= flow_def.max_iterations:
                        logger.warning(f"While loop reached max iterations ({flow_def.max_iterations})")
                        break

                    # Evaluate condition
                    flow_context.update_evaluation_context()

                    # Add loop state to context
                    flow_context.evaluation_context.variables[flow_def.iteration_var] = i

                    # Add previous iteration context if available
                    if flow_def.pass_state and loop_state.context:
                        for key, value in loop_state.context.items():
                            flow_context.evaluation_context.variables[key] = value

                    try:
                        condition_result = flow_context.evaluation_context.evaluate(flow_def.condition_expr)
                        if not condition_result:
                            break

                        # Update loop state
                        loop_state.iteration = i

                        # Execute the loop body
                        flow_context.push_subflow(f"{loop_id}_iteration_{i}")
                        try:
                            await body_orchestrator.run(flow_context)

                            # Capture results if requested
                            if flow_def.capture_results:
                                # Get results for this iteration
                                iteration_results = {}
                                for node_id, result in flow_context.execution_results.items():
                                    # Only include results from the current iteration path
                                    if node_id.startswith(flow_context.get_current_subflow_id()):
                                        iteration_results[node_id] = result

                                loop_state.iteration_results.append(iteration_results)

                            # Store context if pass_state is enabled
                            if flow_def.pass_state:
                                # Save current context state to pass to next iteration
                                loop_state.context = {
                                    key: value
                                    for key, value in flow_context.evaluation_context.variables.items()
                                    if key != "iteration"  # Don't include loop control variables
                                }
                        finally:
                            flow_context.pop_subflow()

                        # Increment iteration counter
                        i += 1

                        # Check for execution failure
                        if flow_context.execution_failed:
                            break

                    except Exception as e:
                        logger.exception(f"Error evaluating while condition: {e}")
                        flow_context.execution_failed = True
                        flow_context.execution_failed_message = f"While loop condition evaluation failed: {e}"
                        break

        except Exception as e:
            logger.exception(f"Error in loop flow: {e}")
            flow_context.execution_status = FlowExecutionStatusEnum.FAILED
            flow_context.execution_failed = True
            flow_context.execution_failed_message = f"Loop flow execution failed: {e}"

        # Include loop results in context
        flow_context.evaluation_context.variables[f"loop_result.{loop_id}"] = {
            "iterations": loop_state.iteration + 1,
            "results": loop_state.iteration_results,
        }

        return flow_context.execution_results

    async def _execute_switch_flow(
        self, flow_context: FlowContext, flow_def: SwitchFlow
    ) -> dict[str, FlowNodeExecutionResult]:
        """Execute a switch flow."""
        # Update evaluation context
        flow_context.update_evaluation_context()

        try:
            # Evaluate switch expression
            switch_value = str(flow_context.evaluation_context.evaluate(flow_def.switch_expr))

            # Determine which case to execute
            if switch_value in flow_def.cases:
                case_flow = flow_def.cases[switch_value]
                case_name = switch_value
            elif flow_def.default:
                case_flow = flow_def.default
                case_name = "default"
            else:
                # No matching case and no default
                logger.info(f"Switch value '{switch_value}' did not match any case and no default provided")
                return {}

            # Create sub-orchestrator for the case
            sub_orchestrator = FlowOrchestrator(flow_definition=case_flow, resource_config=self.resource_config)

            # Execute the case
            flow_context.push_subflow(f"case_{case_name}")
            try:
                await sub_orchestrator.run(flow_context)
            finally:
                flow_context.pop_subflow()

            # Return execution results
            return flow_context.execution_results

        except Exception as e:
            logger.exception(f"Error in switch flow: {e}")
            flow_context.execution_status = FlowExecutionStatusEnum.FAILED
            flow_context.execution_failed = True
            flow_context.execution_failed_message = f"Switch flow execution failed: {e}"
            return {}

    async def _execute_sequential(
        self, flow_context: FlowContext
    ) -> AsyncGenerator | dict[str, FlowNodeExecutionResult]:
        """Execute nodes sequentially"""
        return await self._execute_nodes(flow_context, sequential=True)

    async def _execute_parallel(self, flow_context: FlowContext) -> dict[str, FlowNodeExecutionResult]:
        """Execute nodes in parallel"""
        return await self._execute_nodes(flow_context, sequential=False)

    async def _execute_nodes(
        self,
        flow_context: FlowContext,
        sequential: bool,
        start_index: int = 0,
    ) -> AsyncGenerator | dict[str, FlowNodeExecutionResult]:
        """Core execution logic for both sequential and parallel node processing"""
        nodes_to_process = self.flow_definition.nodes[start_index:]

        if sequential:
            for index, flow_node in enumerate(nodes_to_process, start=start_index):
                result = await self._process_single_node(
                    flow_node=flow_node,
                    flow_context=flow_context,
                    index=index,
                )

                if result is not None:  # Streaming case will return an async generator
                    return result

                if flow_context.execution_failed:
                    flow_context.execution_status = FlowExecutionStatusEnum.FAILED
                    return None

        else:
            # Parallel execution
            tasks = [
                create_task(
                    self._process_single_node(
                        flow_node=flow_node,
                        flow_context=flow_context,
                        index=index,
                    )
                )
                for index, flow_node in enumerate(nodes_to_process, start=start_index)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions from parallel execution
            for result in results:
                if isinstance(result, Exception):
                    flow_context.execution_status = FlowExecutionStatusEnum.FAILED
                    raise result
                if flow_context.execution_failed:
                    flow_context.execution_status = FlowExecutionStatusEnum.FAILED
                    return None

        # Execution completed
        flow_context.completed_at = datetime.now()
        return flow_context.execution_results

    async def _process_single_node(
        self,
        flow_node: FlowNode,
        flow_context: FlowContext,
        index: int,
    ) -> Any:
        """Process a single node and handle its result."""
        flow_context.set_current_node(index)

        flow_node_input = flow_context.get_initial_input()
        handler = self.get_node_execution_handler(flow_node.type)

        if flow_node.is_streaming():
            # Configure streaming flow_context
            flow_context.streaming_contexts[flow_node.identifier] = StreamingContext(
                status=StreamingStatusEnum.STREAMING,
                completion_event=Event(),
            )
            flow_context.current_node_index = index
            # Execute streaming node
            result = await handler.handle(
                flow_node=flow_node,
                flow_node_input=flow_node_input,
                flow_context=flow_context,
                resource_config=self.resource_config,
            )
            if not isinstance(result, AsyncGenerator):
                logger.warning(
                    f"A streaming node handler is expected to returned an AsyncGenerator not{type(result)}. "
                    f"Node {flow_node.identifier}, handler {handler.identifier}"
                )

            return result

        # Execute non-streaming node
        result = await handler.handle(
            flow_node=flow_node,
            flow_node_input=flow_node_input,
            flow_context=flow_context,
            resource_config=self.resource_config,
        )
        return await self._process_single_node_completion(flow_node=flow_node, flow_context=flow_context, result=result)

    async def _process_single_node_completion(
        self,
        flow_node: FlowNode,
        flow_context: FlowContext,
        result,
    ) -> AsyncGenerator | None:
        flow_context.execution_results[flow_context.current_node_identifier] = result
        flow_context.updated_at = datetime.now()

        _result_json = json.dumps(result) if isinstance(result, dict) else result.model_dump_json()

        if flow_context.artifact_manager:
            flow_context.artifact_manager.record_node_output(
                node_identifier=flow_node.identifier,
                output_file_name="node.json",
                output_data=json.loads(_result_json),
            )

        """ TODO
        # Determine if we should send SSE update
        should_send_update = flow_node.response_settings and flow_node.response_settings.send_updates

        if should_send_update:
            if self.response_protocol == ResponseProtocolEnum.HTTP_SSE:
                return self._create_node_execution_sse_generator(result)
            else:
                raise ValueError()
        """

        return None

    async def _continue_after_streaming(self, flow_context: FlowContext) -> None:
        """Continue processing remaining nodes after streaming completes"""
        try:
            # Wait for streaming to complete
            current_streaming_context = flow_context.streaming_contexts[flow_context.current_node_identifier]
            logger.debug(
                f"_continue_after_streaming: waiting for completion at node {flow_context.current_node_identifier}"
            )
            await current_streaming_context.completion_event.wait()
            logger.debug(f"_continue_after_streaming: streaming completed for {flow_context.current_node_identifier}")

            if not current_streaming_context.successfull:
                raise current_streaming_context.error or ValueError("Streaming unsuccessful")

            # NOTE: Streaming result are added to execution results inside notify_streaming_complete()
            # -- flow_context.execution_results[flow_context.current_node_identifier] = current_streaming_context.result
            # Continue with remaining nodes using the same execution strategy
            start_index = flow_context.current_node_index + 1
            if self.flow_definition.execution_strategy == ExecutionStrategyEnum.sequential:
                await self._execute_nodes(flow_context, sequential=True, start_index=start_index)
            else:
                await self._execute_nodes(flow_context, sequential=False, start_index=start_index)

            flow_context.completed_at = datetime.now()
            flow_context.execution_status = FlowExecutionStatusEnum.COMPLETED
            await self.execution_recorder.update_execution_in_db(flow_context)

        except Exception:
            flow_context.execution_status = FlowExecutionStatusEnum.FAILED
            logger.exception("Post-streaming execution failed")
            await self.execution_recorder.update_execution_in_db(flow_context)
            raise

    '''TODO
    def _create_node_execution_sse_generator(self, result: FlowNodeExecutionResult) -> AsyncGenerator:
        """Create an SSE generator for node execution results"""
        async def generator():
            try:
                sse_response = SSENodeExecutionResultResponse(
                    event="node_execution_result",
                    data={
                        "node_identifier": result.node_identifier,
                        "status": result.status,
                        "user_inputs": [input.model_dump() for input in result.user_inputs] if result.user_inputs else None,
                        "node_output": result.node_output.model_dump() if result.node_output else None,
                        "storage_data": result.storage_data,
                        "created_at": result.created_at.isoformat(),
                    },
                )
                yield sse_response

            except Exception as e:
                logger.exception("Error generating SSE response")
                error_response = SSEErrorResponse(
                    data=SSEErrorData(
                        error_code=SSEErrorCode.server_error,
                        message="Error generating node execution result",
                        details={"error": str(e)},
                    ),
                )
                yield error_response

        return generator()


    def _create_final_response(self, flow_context: FlowContext) -> dict[str, Any] | AsyncGenerator:
        """Create final response based on protocol"""
        if self._final_protocol == ResponseProtocolEnum.HTTP:
            return self._create_final_http_response(flow_context)
        else:
            return self._create_final_sse_response(flow_context)

    def _create_final_http_response(self, flow_context: FlowContext) -> dict[str, Any]:
        """Create final HTTP response with all results"""
        return {
            "status": flow_context.execution_status,
            "results": {
                node_id: result.model_dump()
                for node_id, result in flow_context.execution_results.items()
                if (
                    self.flow_definition.nodes[flow_context.get_node_index(node_id)]
                    .response_settings.include_in_final
                )
            },
            "completed_at": flow_context.completed_at.isoformat(),
        }

    def _create_final_sse_response(self, flow_context: FlowContext) -> AsyncGenerator:
        """Create final SSE response"""
        async def generator():
            # Send individual results
            for node_id, result in flow_context.execution_results.items():
                if (
                    self.flow_definition.nodes[flow_context.get_node_index(node_id)]
                    .response_settings.include_in_final
                ):
                    yield SSENodeExecutionResultResponse(
                        event="node_result",
                        data=result.model_dump(),
                    )

            # Send final completion message
            yield SSENodeExecutionResultResponse(
                event="flow_complete",
                data={
                    "status": flow_context.execution_status,
                    "completed_at": flow_context.completed_at.isoformat(),
                },
            )

        return generator()
    '''  # noqa: E501, W505
