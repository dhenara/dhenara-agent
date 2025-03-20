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
from dhenara.agent.engine.types import LegacyFlowContext, LegacyStreamingContext, LegacyStreamingStatusEnum
from dhenara.agent.resource.registry import resource_config_registry
from dhenara.agent.types import (
    ConditionalFlow,
    ExecutionStatusEnum,
    ExecutionStrategyEnum,
    FlowDefinition,
    FlowNodeTypeEnum,
    FlowTypeEnum,
    LegacyFlowNode,
    LoopFlow,
    NodeExecutionResult,
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
        execution_context: LegacyFlowContext,
    ) -> dict[str, NodeExecutionResult] | AIModelCallResponse:
        """Execute the flow with support for control flow."""
        try:
            execution_context.execution_status = ExecutionStatusEnum.RUNNING
            self.execution_recorder = ExecutionRecorder()
            await self.execution_recorder.update_execution_in_db(execution_context, create=True)

            # Handle different flow types
            flow_def = self.flow_definition

            if flow_def.flow_type == FlowTypeEnum.standard:
                # Standard flow with nodes

                if self.flow_definition.execution_strategy == ExecutionStrategyEnum.sequential:
                    result = await self._execute_sequential(execution_context)

                    # if self.has_any_streaming_node():
                    # if isinstance(result, AsyncGenerator):
                    if (
                        isinstance(result, AIModelCallResponse)
                        and result.stream_generator
                        and isinstance(result.stream_generator, AsyncGenerator)
                    ):
                        background_tasks = set()

                        # Create a background task to continue processing after streaming
                        task = create_task(self._continue_after_streaming(execution_context))
                        execution_context.execution_status = ExecutionStatusEnum.PENDING

                        # NOTE: Below 2 lines are from RUFF:RUF006
                        # https://docs.astral.sh/ruff/rules/asyncio-dangling-task/
                        # Add task to the set. This creates a strong reference.
                        background_tasks.add(task)

                        # To prevent keeping references to finished tasks forever,
                        # make each task remove its own reference from the set after completion:
                        task.add_done_callback(background_tasks.discard)

                        return result

                elif flow_def.execution_strategy == ExecutionStrategyEnum.parallel:
                    result = await self._execute_parallel(execution_context)
                else:
                    raise NotImplementedError(f"Unsupported execution strategy: {flow_def.execution_strategy}")

            elif flow_def.flow_type == FlowTypeEnum.condition:
                result = await self._execute_conditional_flow(execution_context, flow_def)

            elif flow_def.flow_type == FlowTypeEnum.loop:
                result = await self._execute_loop_flow(execution_context, flow_def)

            elif flow_def.flow_type == FlowTypeEnum.switch:
                result = await self._execute_switch_flow(execution_context, flow_def)

            else:
                raise NotImplementedError(f"Unsupported flow type: {flow_def.flow_type}")

            # completion logic
            execution_context.execution_status = ExecutionStatusEnum.COMPLETED
            logger.debug(f"execute: Execution completed. execution_results={execution_context.execution_results}")

            await self.execution_recorder.update_execution_in_db(execution_context)
            logger.debug("execute: Finished updating DB")
            return execution_context.execution_results

        except Exception:
            execution_context.execution_status = ExecutionStatusEnum.FAILED
            logger.exception("Flow execution failed")
            raise

    async def _execute_conditional_flow(
        self, execution_context: LegacyFlowContext, flow_def: ConditionalFlow
    ) -> dict[str, NodeExecutionResult]:
        """Execute a conditional flow."""
        # Update evaluation context
        execution_context.update_evaluation_context()

        # Evaluate condition
        try:
            condition_result = execution_context.evaluation_context.evaluate(flow_def.condition_expr)

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
            execution_context.push_subflow(branch_name)

            try:
                await sub_orchestrator.run(execution_context)
            finally:
                execution_context.pop_subflow()

            # Return execution results
            return execution_context.execution_results

        except Exception as e:
            logger.exception(f"Error in conditional flow: {e}")
            execution_context.execution_status = ExecutionStatusEnum.FAILED
            execution_context.execution_failed = True
            execution_context.execution_failed_message = f"Conditional flow execution failed: {e}"
            return {}

    async def _execute_loop_flow(
        self, execution_context: LegacyFlowContext, flow_def: LoopFlow
    ) -> dict[str, NodeExecutionResult]:
        """Execute a loop flow."""
        # Initialize loop state
        loop_id = f"loop_{id(flow_def)}"
        loop_state = execution_context.start_loop(loop_id)

        # Create sub-orchestrator for the loop body
        body_orchestrator = FlowOrchestrator(flow_definition=flow_def.body, resource_config=self.resource_config)

        try:
            if flow_def.loop_type == "for":
                # For loop - evaluate items expression
                execution_context.update_evaluation_context()
                items = execution_context.evaluation_context.evaluate(flow_def.items_expr)

                # Iterate over items
                for i, item in enumerate(items):
                    if flow_def.max_iterations and i >= flow_def.max_iterations:
                        logger.warning(f"Loop reached max iterations ({flow_def.max_iterations})")
                        break

                    # Update loop state
                    loop_state.iteration = i
                    loop_state.item = item

                    # Update evaluation context with loop variables
                    execution_context.evaluation_context.variables[flow_def.iteration_var] = i
                    if flow_def.item_var:
                        execution_context.evaluation_context.variables[flow_def.item_var] = item

                    # Execute the loop body
                    execution_context.push_subflow(f"{loop_id}_iteration_{i}")
                    try:
                        await body_orchestrator.run(execution_context)

                        # Capture results if requested
                        if flow_def.capture_results:
                            # Get results for this iteration
                            iteration_results = {}
                            for node_id, result in execution_context.execution_results.items():
                                # Only include results from the current iteration path
                                if node_id.startswith(execution_context.get_current_subflow_id()):
                                    iteration_results[node_id] = result  # noqa: PERF403 : TODO_FUTURE

                            loop_state.iteration_results.append(iteration_results)

                        # Store context if pass_state is enabled
                        if flow_def.pass_state:
                            # Save current context state to pass to next iteration
                            loop_state.context = {
                                key: value
                                for key, value in execution_context.evaluation_context.variables.items()
                                if key not in ["iteration", "item"]  # Don't include loop control variables
                            }
                    finally:
                        execution_context.pop_subflow()

                    # Check for execution failure
                    if execution_context.execution_failed:
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
                    execution_context.update_evaluation_context()

                    # Add loop state to context
                    execution_context.evaluation_context.variables[flow_def.iteration_var] = i

                    # Add previous iteration context if available
                    if flow_def.pass_state and loop_state.context:
                        for key, value in loop_state.context.items():
                            execution_context.evaluation_context.variables[key] = value

                    try:
                        condition_result = execution_context.evaluation_context.evaluate(flow_def.condition_expr)
                        if not condition_result:
                            break

                        # Update loop state
                        loop_state.iteration = i

                        # Execute the loop body
                        execution_context.push_subflow(f"{loop_id}_iteration_{i}")
                        try:
                            await body_orchestrator.run(execution_context)

                            # Capture results if requested
                            if flow_def.capture_results:
                                # Get results for this iteration
                                iteration_results = {}
                                for node_id, result in execution_context.execution_results.items():
                                    # Only include results from the current iteration path
                                    if node_id.startswith(execution_context.get_current_subflow_id()):
                                        iteration_results[node_id] = result

                                loop_state.iteration_results.append(iteration_results)

                            # Store context if pass_state is enabled
                            if flow_def.pass_state:
                                # Save current context state to pass to next iteration
                                loop_state.context = {
                                    key: value
                                    for key, value in execution_context.evaluation_context.variables.items()
                                    if key != "iteration"  # Don't include loop control variables
                                }
                        finally:
                            execution_context.pop_subflow()

                        # Increment iteration counter
                        i += 1

                        # Check for execution failure
                        if execution_context.execution_failed:
                            break

                    except Exception as e:
                        logger.exception(f"Error evaluating while condition: {e}")
                        execution_context.execution_failed = True
                        execution_context.execution_failed_message = f"While loop condition evaluation failed: {e}"
                        break

        except Exception as e:
            logger.exception(f"Error in loop flow: {e}")
            execution_context.execution_status = ExecutionStatusEnum.FAILED
            execution_context.execution_failed = True
            execution_context.execution_failed_message = f"Loop flow execution failed: {e}"

        # Include loop results in context
        execution_context.evaluation_context.variables[f"loop_result.{loop_id}"] = {
            "iterations": loop_state.iteration + 1,
            "results": loop_state.iteration_results,
        }

        return execution_context.execution_results

    async def _execute_switch_flow(
        self, execution_context: LegacyFlowContext, flow_def: SwitchFlow
    ) -> dict[str, NodeExecutionResult]:
        """Execute a switch flow."""
        # Update evaluation context
        execution_context.update_evaluation_context()

        try:
            # Evaluate switch expression
            switch_value = str(execution_context.evaluation_context.evaluate(flow_def.switch_expr))

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
            execution_context.push_subflow(f"case_{case_name}")
            try:
                await sub_orchestrator.run(execution_context)
            finally:
                execution_context.pop_subflow()

            # Return execution results
            return execution_context.execution_results

        except Exception as e:
            logger.exception(f"Error in switch flow: {e}")
            execution_context.execution_status = ExecutionStatusEnum.FAILED
            execution_context.execution_failed = True
            execution_context.execution_failed_message = f"Switch flow execution failed: {e}"
            return {}

    async def _execute_sequential(
        self, execution_context: LegacyFlowContext
    ) -> AsyncGenerator | dict[str, NodeExecutionResult]:
        """Execute nodes sequentially"""
        return await self._execute_nodes(execution_context, sequential=True)

    async def _execute_parallel(self, execution_context: LegacyFlowContext) -> dict[str, NodeExecutionResult]:
        """Execute nodes in parallel"""
        return await self._execute_nodes(execution_context, sequential=False)

    async def _execute_nodes(
        self,
        execution_context: LegacyFlowContext,
        sequential: bool,
        start_index: int = 0,
    ) -> AsyncGenerator | dict[str, NodeExecutionResult]:
        """Core execution logic for both sequential and parallel node processing"""
        nodes_to_process = self.flow_definition.nodes[start_index:]

        if sequential:
            for index, flow_node in enumerate(nodes_to_process, start=start_index):
                result = await self._process_single_node(
                    flow_node=flow_node,
                    execution_context=execution_context,
                    index=index,
                )

                if result is not None:  # Streaming case will return an async generator
                    return result

                if execution_context.execution_failed:
                    execution_context.execution_status = ExecutionStatusEnum.FAILED
                    return None

        else:
            # Parallel execution
            tasks = [
                create_task(
                    self._process_single_node(
                        flow_node=flow_node,
                        execution_context=execution_context,
                        index=index,
                    )
                )
                for index, flow_node in enumerate(nodes_to_process, start=start_index)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions from parallel execution
            for result in results:
                if isinstance(result, Exception):
                    execution_context.execution_status = ExecutionStatusEnum.FAILED
                    raise result
                if execution_context.execution_failed:
                    execution_context.execution_status = ExecutionStatusEnum.FAILED
                    return None

        # Execution completed
        execution_context.completed_at = datetime.now()
        return execution_context.execution_results

    async def _process_single_node(
        self,
        flow_node: LegacyFlowNode,
        execution_context: LegacyFlowContext,
        index: int,
    ) -> Any:
        """Process a single node and handle its result."""
        execution_context.set_current_node(index)

        flow_node_input = execution_context.get_initial_input()
        handler = self.get_node_execution_handler(flow_node.type)

        if flow_node.is_streaming():
            # Configure streaming execution_context
            execution_context.streaming_contexts[flow_node.identifier] = LegacyStreamingContext(
                status=LegacyStreamingStatusEnum.STREAMING,
                completion_event=Event(),
            )
            execution_context.current_node_index = index
            # Execute streaming node
            result = await handler.handle(
                flow_node=flow_node,
                flow_node_input=flow_node_input,
                execution_context=execution_context,
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
            execution_context=execution_context,
            resource_config=self.resource_config,
        )
        return await self._process_single_node_completion(
            flow_node=flow_node, execution_context=execution_context, result=result
        )

    async def _process_single_node_completion(
        self,
        flow_node: LegacyFlowNode,
        execution_context: LegacyFlowContext,
        result,
    ) -> AsyncGenerator | None:
        execution_context.execution_results[execution_context.current_node_identifier] = result
        execution_context.updated_at = datetime.now()

        _result_json = json.dumps(result) if isinstance(result, dict) else result.model_dump_json()

        if execution_context.artifact_manager:
            execution_context.artifact_manager.record_node_output(
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

    async def _continue_after_streaming(self, execution_context: LegacyFlowContext) -> None:
        """Continue processing remaining nodes after streaming completes"""
        try:
            # Wait for streaming to complete
            current_streaming_context = execution_context.streaming_contexts[execution_context.current_node_identifier]
            logger.debug(
                f"_continue_after_streaming: waiting for completion at node {execution_context.current_node_identifier}"
            )
            await current_streaming_context.completion_event.wait()
            logger.debug(
                f"_continue_after_streaming: streaming completed for {execution_context.current_node_identifier}"
            )

            if not current_streaming_context.successfull:
                raise current_streaming_context.error or ValueError("Streaming unsuccessful")

            # NOTE: Streaming result are added to execution results inside notify_streaming_complete()
            # -- execution_context.execution_results[exe_ctx.current_node_identifier] = current_streaming_context.result
            # Continue with remaining nodes using the same execution strategy
            start_index = execution_context.current_node_index + 1
            if self.flow_definition.execution_strategy == ExecutionStrategyEnum.sequential:
                await self._execute_nodes(execution_context, sequential=True, start_index=start_index)
            else:
                await self._execute_nodes(execution_context, sequential=False, start_index=start_index)

            execution_context.completed_at = datetime.now()
            execution_context.execution_status = ExecutionStatusEnum.COMPLETED
            await self.execution_recorder.update_execution_in_db(execution_context)

        except Exception:
            execution_context.execution_status = ExecutionStatusEnum.FAILED
            logger.exception("Post-streaming execution failed")
            await self.execution_recorder.update_execution_in_db(execution_context)
            raise

    '''TODO
    def _create_node_execution_sse_generator(self, result: NodeExecutionResult) -> AsyncGenerator:
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


    def _create_final_response(self, execution_context: LegacyFlowContext) -> dict[str, Any] | AsyncGenerator:
        """Create final response based on protocol"""
        if self._final_protocol == ResponseProtocolEnum.HTTP:
            return self._create_final_http_response(execution_context)
        else:
            return self._create_final_sse_response(execution_context)

    def _create_final_http_response(self, execution_context: LegacyFlowContext) -> dict[str, Any]:
        """Create final HTTP response with all results"""
        return {
            "status": execution_context.execution_status,
            "results": {
                node_id: result.model_dump()
                for node_id, result in execution_context.execution_results.items()
                if (
                    self.flow_definition.nodes[execution_context.get_node_index(node_id)]
                    .response_settings.include_in_final
                )
            },
            "completed_at": execution_context.completed_at.isoformat(),
        }

    def _create_final_sse_response(self, execution_context: LegacyFlowContext) -> AsyncGenerator:
        """Create final SSE response"""
        async def generator():
            # Send individual results
            for node_id, result in execution_context.execution_results.items():
                if (
                    self.flow_definition.nodes[execution_context.get_node_index(node_id)]
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
                    "status": execution_context.execution_status,
                    "completed_at": execution_context.completed_at.isoformat(),
                },
            )

        return generator()
    '''  # noqa: E501, W505
