from abc import ABC, abstractmethod
from typing import Any

from dhenara.agent.engine.types import FlowContext
from dhenara.agent.types import (
    FlowNode,
    FlowNodeInput,
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
        flow_node: FlowNode,
        flow_node_input: FlowNodeInput,
        flow_context: FlowContext,
        resource_config: ResourceConfig,
    ) -> Any:
        """
        Handle the execution of a flow node.
        """
        pass

    def set_node_execution_failed(self, flow_node: FlowNode, flow_context: FlowContext, message):
        flow_context.execution_failed = True
        flow_context.execution_failed_message = message

    async def process_input_contents_and_node_prompt(
        self,
        flow_node: FlowNode,
        flow_node_input: FlowNodeInput,
        model: AIModel,
    ) -> list[dict]:
        final_content = await flow_node.get_full_input_content(
            node_input=flow_node_input,
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
        flow_node: FlowNode,
        flow_context: FlowContext,
        model: AIModel,
    ) -> list:
        context_sources = flow_node.input_settings.context_sources
        outputs_as_prompts = []
        try:
            for source_node_identifier in context_sources:
                if source_node_identifier == SpecialNodeIdEnum.PREVIOUS:
                    previous_node_identifier = flow_context.flow_definition.get_previous_node_identifier(
                        flow_node.identifier,
                    )
                    previous_node_execution_result = flow_context.execution_results.get(previous_node_identifier)
                else:
                    previous_node_execution_result = flow_context.execution_results.get(source_node_identifier)

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
