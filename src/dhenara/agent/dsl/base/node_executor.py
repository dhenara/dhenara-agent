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
    NodeExecutionResult,
    NodeID,
    NodeInput,
    NodeSettings,
)
from dhenara.agent.dsl.events import NodeInputRequiredEvent
from dhenara.ai.types.resource import ResourceConfig

logger = logging.getLogger(__name__)


ContextT = TypeVar("ContextT", bound=ExecutionContext)


class NodeExecutor(ABC):
    """Base handler for executing flow nodes.

    All node type handlers should inherit from this class and implement
    the handle method to process their specific node type.
    """

    input_model: type[NodeInput] | None
    setting_model: type[NodeSettings]

    def __init__(
        self,
        identifier: str,
    ):
        self.identifier = identifier

    async def get_input_for_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
    ) -> NodeInput:
        """Get input for a node, trying static inputs first then event handlers."""
        # Check static inputs first
        if node_id in execution_context.run_context.static_inputs:
            return execution_context.run_context.static_inputs[node_id]

        if NodeInputRequiredEvent.type in node_definition.pre_events:
            node_input = await self.tirgger_event_node_input_required(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
            )

            return node_input

        logger.debug(f"Failed to fetch inputs for node {node_id}")
        return None

    # Inbuild  events
    async def tirgger_event_node_input_required(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
    ) -> NodeInput:
        # Request input via event
        event = NodeInputRequiredEvent(node_id, node_definition.node_type)
        await execution_context.run_context.event_bus.publish(event)

        # Check if any handler provided input
        if event.handled and event.input:
            node_input = event.input
            logger.debug(f"{node_id}: Node input via event {event.type} is {node_input}")
        else:
            # No input provided by any handler
            logger.error(f"{node_id}: No input provided for node via event {event.type}")
            node_input = None

        return node_input

    async def execute(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
    ) -> Any:
        resource_config: ResourceConfig = execution_context.resource_config

        logger.debug("Waiting for node input")

        node_input = None
        if node_definition.pre_execute_input_required:
            node_input = await self.get_input_for_node(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
            )
            logger.debug(f"Node Input: {node_input}")

            if not isinstance(node_input, self.input_model):
                raise ValueError(
                    f"Input validation failed. Expects type of {self.input_model} but got a type of {type(node_input)}"
                )

        logger.debug("Node input received")

        # Record node input if configured
        input_record_settings = node_definition.record_settings.input if node_definition.record_settings else None
        input_git_settings = node_definition.git_settings.input if node_definition.git_settings else None
        if input_record_settings and input_record_settings.enabled:
            input_data = node_input.model_dump() if hasattr(node_input, "model_dump") else node_input
            execution_context.artifact_manager.record_data(
                record_type="input",
                node_identifier=node_id,
                data=input_data,
                record_settings=input_record_settings,
                git_settings=input_git_settings,
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

        # TODO_FUTURE
        ## Determine if we should send SSE update
        # should_send_update = flow_node.response_settings and flow_node.response_settings.send_updates

        # if should_send_update:
        #    if self.response_protocol == ResponseProtocolEnum.HTTP_SSE:
        #        return self._create_node_execution_sse_generator(result)
        #    else:
        #        raise ValueError()

        return await self.record_results(
            node_id=node_id,
            node_definition=node_definition,
            execution_context=execution_context,
        )

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

    async def record_results(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ContextT,
    ) -> AsyncGenerator | None:
        if execution_context.artifact_manager:
            result: NodeExecutionResult | None = execution_context.execution_results.get(node_id, None)

            if not result:
                logger.info("No result found in execution context. Skipping records")
                return False

            execution_context.updated_at = datetime.now()
            # Get record settings from the node if available
            output_record_settings = None
            output_record_settings = None
            output_git_settings = None
            outcome_git_settings = None

            if node_definition.record_settings:
                output_record_settings = node_definition.record_settings.output
                outcome_record_settings = node_definition.record_settings.outcome
            if node_definition.git_settings:
                output_git_settings = node_definition.git_settings.output
                outcome_git_settings = node_definition.git_settings.outcome

            output_data = result.node_output.data
            outcome_data = result.node_outcome.data

            output_data = output_data.model_dump() if hasattr(output_data, "model_dump") else output_data
            outcome_data = outcome_data.model_dump() if hasattr(outcome_data, "model_dump") else outcome_data

            # Record the node output
            execution_context.artifact_manager.record_data(
                record_type="output",
                node_identifier=node_id,
                data=output_data,
                record_settings=output_record_settings,
                git_settings=output_git_settings,
            )

            # Record the node outcome
            execution_context.artifact_manager.record_data(
                record_type="outcome",
                node_identifier=node_id,
                data=outcome_data,
                record_settings=outcome_record_settings,
                git_settings=outcome_git_settings,
            )

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
