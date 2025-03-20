from abc import ABC, abstractmethod
from typing import Any

from dhenara.agent.dsl.base import ExecutableNodeDefinition, ExecutionContext
from dhenara.agent.types import (
    NodeInput,
    SpecialNodeIdEnum,
)
from dhenara.ai.providers.common import PromptFormatter
from dhenara.ai.types import (
    AIModel,
)
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError


class NodeHandler(ABC):
    """Base handler for executing flow nodes.

    All node type handlers should inherit from this class and implement
    the handle method to process their specific node type.
    """

    def __init__(
        self,
        identifier: str,
    ):
        self.identifier = identifier

    @abstractmethod
    async def handle(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
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

    async def process_input_contents_and_node_prompt(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        model: AIModel,
    ) -> list[dict]:
        final_content = await node_definition.get_full_input_content(
            node_input=node_input,
            # TODO: kwargs
        )

        prompts = PromptFormatter.format_conversion_node_as_prompts(
            model=model,
            user_query=final_content,
            attached_files=[],
            previous_response=None,
            max_words_query=None,
            max_words_files=None,
            max_words_response=None,
        )
        return prompts[0]

    async def get_previous_node_outputs_as_prompts(
        self,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        model: AIModel,
    ) -> list:
        context_sources = node_definition.input_settings.context_sources if node_definition.input_settings else []
        outputs_as_prompts = []
        try:
            for source_node_identifier in context_sources:
                if source_node_identifier == SpecialNodeIdEnum.PREVIOUS:
                    previous_node_identifier = execution_context.flow_definition.get_previous_node_identifier(
                        execution_context.current_node_identifier,
                    )
                    previous_node_execution_result = execution_context.execution_results.get(previous_node_identifier)
                else:
                    previous_node_execution_result = execution_context.execution_results.get(source_node_identifier)

                previous_node_output = previous_node_execution_result.node_output.data

                # TODO: Check if node is saved to DB as ConversationNode and , and get it from that
                # For now processing execution results text contents

                prompts = PromptFormatter.format_conversion_node_as_prompts(
                    model=model,
                    user_query=None,
                    attached_files=[],  # TODO: Get from user inputs
                    previous_response=previous_node_output.response.full_response,
                    max_words_query=None,
                    max_words_files=None,
                    max_words_response=None,
                )

                outputs_as_prompts += prompts

        except Exception as e:
            raise DhenaraAPIError(f"previous_node_output: Error: {e}")

        return outputs_as_prompts
