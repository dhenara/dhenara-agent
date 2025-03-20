import json
from abc import abstractmethod
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, Generic, TypeVar

from dhenara.agent.dsl.base import ExecutableNodeOutcomeSettings, ExecutionContext
from dhenara.agent.types.base import BaseModelABC
from dhenara.agent.types.flow import (
    ExecutionStatusEnum,
    ExecutionStrategyEnum,
    NodeInput,
)
from dhenara.ai.types.resource import ResourceConfigItem

ContextT = TypeVar("ContextT", bound=ExecutionContext)


class ExecutableNodeDefinition(BaseModelABC, Generic[ContextT]):  # Abstract Class
    """Base class for all node definitions."""

    outcome_settings: ExecutableNodeOutcomeSettings | None = None
    streaming: bool = False  # TODO

    class Config:
        arbitrary_types_allowed = True  # TODO: Review

    # @abstractmethod
    async def execute(
        self,
        execution_context: ContextT,
        node_input: NodeInput,
        # resource_config: ResourceConfig,
    ) -> Any:
        # self.resource_config = resource_config

        """Execute this node definition."""
        pass
        result = await self.process_node(
            execution_context=execution_context,
            node_input=node_input,
        )

        if result is not None:  # Streaming case will return an async generator
            return result

        if execution_context.execution_failed:
            execution_context.execution_status = ExecutionStatusEnum.FAILED
            return None

    @abstractmethod
    def get_handler(self):  # NodeHandler:
        """Get the handler for this node definition."""
        pass

    async def process_node(
        self,
        execution_context: ContextT,
        node_input: NodeInput,
    ) -> Any:
        """Process a single node and handle its result."""
        handler = self.get_handler()

        # if self.is_streaming:
        #    # Configure streaming execution_context
        #    execution_context.streaming_contexts[execution_context.current_node_identifier] = StreamingContext(
        #        status=StreamingStatusEnum.STREAMING,
        #        completion_event=Event(),
        #    )
        #    execution_context.current_node_index = index
        #    # Execute streaming node
        #    result = await handler.handle(
        #        flow_node=flow_node,
        #        flow_node_input=flow_node_input,
        #        execution_context=execution_context,
        #        resource_config=self.resource_config,
        #    )
        #    if not isinstance(result, AsyncGenerator):
        #        execution_context.logger.warning(
        #            f"A streaming node handler is expected to returned an AsyncGenerator not{type(result)}. "
        #            f"Node {flow_node.identifier}, handler {handler.identifier}"
        #        )

        #    return result

        # Execute non-streaming node
        result = await handler.handle(
            node_definition=self,  # TODO: Change type in handler
            node_input=node_input,
            execution_context=execution_context,
            resource_config=execution_context.resource_config,
        )
        return await self.process_node_completion(execution_context=execution_context, result=result)

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

    # -------------------------------------------------------------------------
    async def get_full_input_content(
        self,
        node_id: str,
        node_input: NodeInput,
    ) -> str:
        if node_input is None:
            raise ValueError(f"node_input is missing for node {node_id}")

        prompt_variables = node_input.variables or {}
        node_prompt = self.ai_settings.node_prompt if self.ai_settings and self.ai_settings.node_prompt else None
        input_content = node_input.content.get_content() if node_input and node_input.content else None

        if node_prompt:
            if input_content is None:
                input_content = ""  # NOTE: An empty string is better that the word None

            prompt_variables.update({"dh_input_content": input_content})

            return node_prompt.format(**prompt_variables)

        else:
            if not input_content:
                raise ValueError(f"Illegal Node setting for node {node_id}:  node_prompt and input_content are empty")

            return input_content

    def is_streaming(self):
        return self.streaming

    def check_resource_in_node(self, resource: ResourceConfigItem) -> bool:
        """
        Checks if a given resource exists in the node's resource list.

        Args:
            resource: ResourceConfigItem object to check for

        Returns:
            bool: True if the resource exists in the node's resources, False otherwise
        """
        if not self.resources:
            return False

        return any(existing_resource.is_same_as(resource) for existing_resource in self.resources)
