from abc import ABC, abstractmethod
from typing import Any

from dhenara.agent.types import (
    FlowContext,
    FlowNode,
    ResourceConfigItem,
    SpecialNodeIdEnum,
    UserInput,
)

# from common.csource.apps.model_apps.app_ai_connect.libs.tsg.orchestrator import AIModelCallOrchestrator
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
    async def handle(self, flow_node: FlowNode, context: FlowContext, resource_config: ResourceConfig) -> Any:
        """
        Handle the execution of a flow node.

        Args:
            flow_node: The node to execute
            context: The current flow execution context

        Returns:
            The result of node execution
        """
        pass

    def get_user_selected_resources(self, flow_node: FlowNode, context: FlowContext) -> list[ResourceConfigItem]:
        user_input_sources = flow_node.input_settings.input_source.user_input_sources
        resources = []
        for input_source in user_input_sources:
            if input_source == SpecialNodeIdEnum.FULL:
                resources = context.initial_input.resources
            else:
                raise ValueError(f"user_input_source={input_source} not supported, only 'full' is supported now")
        return resources

    def get_user_inputs(self, flow_node: FlowNode, context: FlowContext) -> list[UserInput]:
        user_input_sources = flow_node.input_settings.input_source.user_input_sources
        user_inputs = []
        for input_source in user_input_sources:
            if input_source == SpecialNodeIdEnum.FULL:
                user_inputs.append(context.initial_input.user_input)
            else:
                raise ValueError(
                    f"user_input_source={input_source} not supported for input selection. Only 'full' is supported now"
                )

        return user_inputs

    def set_node_execution_failed(self, flow_node: FlowNode, context: FlowContext, message):
        context.execution_failed = True
        context.execution_failed_message = message

    async def process_user_inputs_and_node_prompt(
        self,
        flow_node: FlowNode,
        user_inputs: list[UserInput],
        model: AIModel,
    ) -> list[dict]:
        # user_input_content = " ".join([await user_input.get_content() for user_input in user_inputs])
        # logger.debug(f"call_ai_model: user_input_content={user_input_content}")

        ## If
        # node_prompt = flow_node.ai_settings.node_prompt
        # has_full_node_prompt = node_prompt and node_prompt.prompt

        # if user_inputs and has_full_node_prompt:
        #    raise ValueError(
        #        f"Illegal input settings for node {flow_node.identifier}.
        #       Conflicting `node_prompt` and `user_inputs` settings. \
        #        Eventhhogh this is taken care in node validation fn `validate_input_settings`, somethhing messed up."
        #    )

        # if has_full_node_prompt:
        #    final_content = node_prompt.format(user_prompt=user_input_content)
        # else:
        #    if node_prompt:  # Process to add `pre` and `post` prompts
        #        final_content = node_prompt.get_prompt(user_prompt=user_input_content)
        #    else:
        #        final_content = user_input_content

        final_content = await flow_node.get_full_input_content(
            user_inputs=user_inputs,
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
        context: FlowContext,
        model: AIModel,
    ) -> list:
        context_sources = flow_node.input_settings.input_source.context_sources
        outputs_as_prompts = []
        try:
            for source_node_identifier in context_sources:
                if source_node_identifier == SpecialNodeIdEnum.PREVIOUS:
                    previous_node_identifier = context.flow_definition.get_previous_node_identifier(
                        flow_node.identifier,
                    )
                    previous_node_execution_result = context.execution_results.get(previous_node_identifier)
                else:
                    previous_node_execution_result = context.execution_results.get(source_node_identifier)

                previous_node_output = previous_node_execution_result.node_output.data

                # TODO: Check if node is saved to DB as ConversationNode and , and get it from that
                # For now processing execution results text contents

                prevnode_userinput = previous_node_execution_result.user_inputs[0]
                if prevnode_userinput:
                    question = prevnode_userinput.primary_content
                else:
                    question = None

                prompts = PromptFormatter.format_conversion_node_as_prompts(
                    model=model,
                    user_query=question,
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
