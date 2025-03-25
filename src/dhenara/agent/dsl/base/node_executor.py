import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, TypeVar

from dhenara.agent.dsl.base import (
    ExecutableNodeDefinition,
    ExecutionContext,
    ExecutionStatusEnum,
    ExecutionStrategyEnum,
    NodeID,
    NodeInput,
    NodeSettings,
)
from dhenara.ai.types.resource import ResourceConfig

logger = logging.getLogger(__name__)


ContextT = TypeVar("ContextT", bound=ExecutionContext)


class NodeExecutor(ABC):
    """Base handler for executing flow nodes.

    All node type handlers should inherit from this class and implement
    the handle method to process their specific node type.
    """

    input_model: type[NodeInput]
    setting_model: type[NodeSettings]
    output_data_model: type

    def __init__(
        self,
        identifier: str,
    ):
        self.identifier = identifier

    def set_inputs_and_settings(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        resource_config: ResourceConfig,
    ) -> Any:
        initial_input = execution_context.get_initial_input()
        node_input = node_input if node_input is not None else initial_input
        if node_input is None:
            raise ValueError("Failed to get inputs for node ")

    async def execute(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
    ) -> Any:
        # initial_inputs=initial_inputs,
        resource_config: ResourceConfig = execution_context.resource_config

        logger.info("Waiting for node input")
        # TODO:
        # if node.input_setting.type = "static"
        # elif node.input_setting.type = "daynamic"
        node_input = await self.get_live_input()
        logger.debug(f"Node Input: {node_input}")

        if not isinstance(node_input, self.input_model):
            raise ValueError(
                f"Input validation failed. Expects a type of {self.input_model} but got a type of {type(node_input)}"
            )

        # if self.is_streaming:
        #    # Configure streaming execution_context
        #    execution_context.streaming_contexts[execution_context.current_node_identifier] = StreamingContext(
        #        status=StreamingStatusEnum.STREAMING,
        #        completion_event=Event(),
        #    )
        #    execution_context.current_node_index = index
        #    # Execute streaming node
        #    result = await node_executor.handle(
        #        flow_node=flow_node,
        #        flow_node_input=flow_node_input,
        #        execution_context=execution_context,
        #        resource_config=self.resource_config,
        #    )
        #    if not isinstance(result, AsyncGenerator):
        #        execution_context.logger.warning(
        #            f"A streaming node node_executor is expected to returned an AsyncGenerator not{type(result)}. "
        #            f"Node {flow_node.identifier}, node_executor {node_executor.identifier}"
        #        )

        #    return result

        result = await self.execute_node(
            node_id=node_id,
            node_definition=node_definition,
            execution_context=execution_context,
            node_input=node_input,
            resource_config=resource_config,
        )
        logger.debug(f"Node Execution completed: resuult= {result}")
        return await self.process_node_completion(execution_context=execution_context, result=result)

    async def get_live_input(self):
        raise NotImplementedError("get_live_input is not implemented but called by executor")

    @abstractmethod
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        node_input: NodeInput,
        resource_config: ResourceConfig,
    ) -> Any:
        """
        Handle the execution of a flow node.
        """
        pass

    def set_node_execution_failed(
        self,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        message: str,
    ):
        execution_context.execution_failed = True
        execution_context.execution_failed_message = message

    async def process_node_completion(
        self,
        execution_context: ContextT,
        result,
    ) -> AsyncGenerator | None:
        execution_context.execution_results[execution_context.current_node_identifier] = result
        execution_context.updated_at = datetime.now()

        _result_json = json.dumps(result) if isinstance(result, dict) else result.model_dump_json()

        if execution_context.artifact_manager:
            execution_context.artifact_manager.record_node_output(
                node_identifier=execution_context.current_node_identifier,
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

    async def _continue_after_streaming(self, execution_context: ContextT) -> None:
        """Continue processing remaining nodes after streaming completes"""
        try:
            # Wait for streaming to complete
            current_streaming_context = execution_context.streaming_contexts[execution_context.current_node_identifier]
            execution_context.logger.debug(
                f"_continue_after_streaming: waiting for completion at node {execution_context.current_node_identifier}"
            )
            await current_streaming_context.completion_event.wait()
            execution_context.logger.debug(
                f"_continue_after_streaming: streaming completed for {execution_context.current_node_identifier}"
            )

            if not current_streaming_context.successfull:
                raise current_streaming_context.error or ValueError("Streaming unsuccessful")

            # NOTE: Streaming result are added to execution results inside notify_streaming_complete()
            # -- execution_context.execution_results[execution_context.current_node_identifier] = c_str_context.result
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
            execution_context.logger.exception("Post-streaming execution failed")
            await self.execution_recorder.update_execution_in_db(execution_context)
            raise
