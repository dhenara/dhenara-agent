# Copyright 2024-2025 Dhenara Inc. All rights reserved.
# flow_orchestrator.py
#  from tenacity import retry, stop_after_attempt, wait_exponential : TODO Future
import asyncio
import logging
from asyncio import Event, create_task
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from dhenara.agent.engine import NodeHandler, node_handler_registry
from dhenara.agent.resource.registry import resource_config_registry
from dhenara.agent.types import (
    ExecutionStrategyEnum,
    FlowContext,
    FlowDefinition,
    FlowExecutionStatusEnum,
    FlowNode,
    FlowNodeExecutionResult,
    FlowNodeTypeEnum,
    StreamingContext,
    StreamingStatusEnum,
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

    async def execute(self, context: FlowContext) -> dict[str, FlowNodeExecutionResult] | AIModelCallResponse:
        """Execute the flow with streaming support"""

        try:
            context.execution_status = FlowExecutionStatusEnum.RUNNING
            self.execution_recorder = ExecutionRecorder()
            await self.execution_recorder.update_execution_in_db(context, create=True)

            if self.flow_definition.execution_strategy == ExecutionStrategyEnum.sequential:
                result = await self._execute_sequential(context)

                # if self.has_any_streaming_node():
                # if isinstance(result, AsyncGenerator):
                if (
                    isinstance(result, AIModelCallResponse)
                    and result.stream_generator
                    and isinstance(result.stream_generator, AsyncGenerator)
                ):
                    background_tasks = set()

                    # Create a background task to continue processing after streaming
                    task = create_task(self._continue_after_streaming(context))
                    context.execution_status = FlowExecutionStatusEnum.PENDING

                    # NOTE: Below 2 lines are from RUFF:RUF006
                    # https://docs.astral.sh/ruff/rules/asyncio-dangling-task/
                    # Add task to the set. This creates a strong reference.
                    background_tasks.add(task)

                    # To prevent keeping references to finished tasks forever,
                    # make each task remove its own reference from the set after completion:
                    task.add_done_callback(background_tasks.discard)

                    return result

            elif self.flow_definition.execution_strategy == ExecutionStrategyEnum.parallel:
                # TODO: Missing fns
                result = await self._execute_parallel(context)

            else:
                raise NotImplementedError(f"Unsupported execution strategy: {self.flow_definition.execution_strategy}")
            context.execution_status = FlowExecutionStatusEnum.COMPLETED
            logger.debug(f"execute: Execution completed. execution_results={context.execution_results}")

            await self.execution_recorder.update_execution_in_db(context)
            logger.debug("execute: Finished updating DB")
            return context.execution_results

        except Exception:
            context.execution_status = FlowExecutionStatusEnum.FAILED
            logger.exception("Flow execution failed")
            raise

    async def _execute_sequential(self, context: FlowContext) -> AsyncGenerator | dict[str, FlowNodeExecutionResult]:
        """Execute nodes sequentially"""
        return await self._execute_nodes(context, sequential=True)

    async def _execute_parallel(self, context: FlowContext) -> dict[str, FlowNodeExecutionResult]:
        """Execute nodes in parallel"""
        return await self._execute_nodes(context, sequential=False)

    async def _execute_nodes(
        self,
        context: FlowContext,
        sequential: bool,
        start_index: int = 0,
    ) -> AsyncGenerator | dict[str, FlowNodeExecutionResult]:
        """Core execution logic for both sequential and parallel node processing"""
        nodes_to_process = self.flow_definition.nodes[start_index:]

        if sequential:
            for index, flow_node in enumerate(nodes_to_process, start=start_index):
                result = await self._process_single_node(flow_node, context, index)

                if result is not None:  # Streaming case will return an async generator
                    return result

                if context.execution_failed:
                    context.execution_status = FlowExecutionStatusEnum.FAILED
                    return None

        else:
            # Parallel execution
            tasks = [
                create_task(
                    self._process_single_node(
                        flow_node,
                        context,
                        index,
                    )
                )
                for index, flow_node in enumerate(nodes_to_process, start=start_index)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions from parallel execution
            for result in results:
                if isinstance(result, Exception):
                    context.execution_status = FlowExecutionStatusEnum.FAILED
                    raise result
                if context.execution_failed:
                    context.execution_status = FlowExecutionStatusEnum.FAILED
                    return None

        # Execution completed
        context.completed_at = datetime.now()
        return context.execution_results

    async def _process_single_node(
        self,
        flow_node: FlowNode,
        context: FlowContext,
        index: int,
    ) -> Any:
        """Process a single node and handle its result."""
        context.set_current_node(index)
        handler = self.get_node_execution_handler(flow_node.type)

        if flow_node.is_streaming():
            # Configure streaming context
            context.streaming_contexts[flow_node.identifier] = StreamingContext(
                status=StreamingStatusEnum.STREAMING,
                completion_event=Event(),
            )
            context.current_node_index = index
            # Execute streaming node
            result = await handler.handle(flow_node, context, self.resource_config)
            if not isinstance(result, AsyncGenerator):
                logger.warning(
                    f"A streaming node handler is expected to returned an AsyncGenerator not{type(result)}. "
                    f"Node {flow_node.identifier}, handler {handler.identifier}"
                )

            return result

        # Execute non-streaming node
        result = await handler.handle(flow_node, context, self.resource_config)
        return await self._process_single_node_completion(flow_node=flow_node, context=context, result=result)

    async def _process_single_node_completion(
        self,
        flow_node: FlowNode,
        context: FlowContext,
        result,
    ) -> AsyncGenerator | None:
        context.execution_results[context.current_node_identifier] = result
        context.updated_at = datetime.now()

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

    async def _continue_after_streaming(self, context: FlowContext) -> None:
        """Continue processing remaining nodes after streaming completes"""
        try:
            # Wait for streaming to complete
            current_streaming_context = context.streaming_contexts[context.current_node_identifier]
            logger.debug(f"_continue_after_streaming: waiting for completion at node {context.current_node_identifier}")
            await current_streaming_context.completion_event.wait()
            logger.debug(f"_continue_after_streaming: streaming completed for {context.current_node_identifier}")

            if not current_streaming_context.successfull:
                raise current_streaming_context.error or ValueError("Streaming unsuccessful")

            # NOTE: Streaming result are added to execution results inside notify_streaming_complete()
            # -- context.execution_results[context.current_node_identifier] = current_streaming_context.result
            # Continue with remaining nodes using the same execution strategy
            start_index = context.current_node_index + 1
            if self.flow_definition.execution_strategy == ExecutionStrategyEnum.sequential:
                await self._execute_nodes(context, sequential=True, start_index=start_index)
            else:
                await self._execute_nodes(context, sequential=False, start_index=start_index)

            context.completed_at = datetime.now()
            context.execution_status = FlowExecutionStatusEnum.COMPLETED
            await self.execution_recorder.update_execution_in_db(context)

        except Exception:
            context.execution_status = FlowExecutionStatusEnum.FAILED
            logger.exception("Post-streaming execution failed")
            await self.execution_recorder.update_execution_in_db(context)
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


    def _create_final_response(self, context: FlowContext) -> dict[str, Any] | AsyncGenerator:
        """Create final response based on protocol"""
        if self._final_protocol == ResponseProtocolEnum.HTTP:
            return self._create_final_http_response(context)
        else:
            return self._create_final_sse_response(context)

    def _create_final_http_response(self, context: FlowContext) -> dict[str, Any]:
        """Create final HTTP response with all results"""
        return {
            "status": context.execution_status,
            "results": {
                node_id: result.model_dump()
                for node_id, result in context.execution_results.items()
                if (
                    self.flow_definition.nodes[context.get_node_index(node_id)]
                    .response_settings.include_in_final
                )
            },
            "completed_at": context.completed_at.isoformat(),
        }

    def _create_final_sse_response(self, context: FlowContext) -> AsyncGenerator:
        """Create final SSE response"""
        async def generator():
            # Send individual results
            for node_id, result in context.execution_results.items():
                if (
                    self.flow_definition.nodes[context.get_node_index(node_id)]
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
                    "status": context.execution_status,
                    "completed_at": context.completed_at.isoformat(),
                },
            )

        return generator()
    '''  # noqa: E501, W505
