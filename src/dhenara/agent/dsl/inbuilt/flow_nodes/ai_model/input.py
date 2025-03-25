from typing import Any, NewType

from pydantic import Field

from dhenara.agent.dsl.base import NodeInput
from dhenara.ai.types import ResourceConfigItem

from .settings import AIModelNodeSettings

NodeID = NewType("NodeID", str)
FlowIdentifier = NewType("FlowIdentifier", str)


class AIModelNodeInput(NodeInput):
    settings_override: AIModelNodeSettings | None = Field(
        default=None,
        description="Optional settings override",
    )

    # Replacement for prompt variables
    prompt_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Variables for template resolution in prompt",
        example={"style": "modern", "name": "Annie"},
    )
    instruction_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Variables for template resolution in system instructions",
        example={"style": "modern", "name": "Annie"},
    )

    # Resouce overrides
    resources: list[ResourceConfigItem] = Field(
        default_factory=list,
        description="List of resources to be used",
    )

    # AIModel Options overrides
    # options: dict[str, Any] = Field(
    #    default_factory=dict,
    #    description="Configuration options for the AI model behavior",
    #    example={
    #        "temperature": 0.7,
    #        "max_output_tokens": 100,
    #        "top_p": 1.0,
    #    },
    # )

    # NOTE:
    # `is_default` validations for resoures are added inside flow models,
    # note input models

    # @model_validator(mode="after")
    # def validate_action_requirements(self) -> "NodeInput":
    #    node_objects = [
    #        obj for obj in self.internal_data_objs if obj.object_type == InternalDataObjectTypeEnum.conversation_node
    #    ]

    #    if self.content.action == FlowNodeUserInputActionEnum.regenerate_conversation_node:
    #        current_nodes = [obj for obj in node_objects if obj.object_scope == InternalDataObjParamsScopeEnum.current]
    #        parent_nodes = [obj for obj in node_objects if obj.object_scope == InternalDataObjParamsScopeEnum.parent]

    #        if not (len(current_nodes) == 1 and len(parent_nodes) == 1):
    #            raise ValueError("Regenerate action requires exactly one current and one parent node")

    #    return self

    def get_options(self, default: dict | None = None) -> dict[str, Any]:
        """Get options with optional defaults.

        Args:
            default: Default options to use if none are set

        Returns:
            Dictionary of options, merged with defaults if provided
        """
        if default is None:
            default = {}

        if self.options is None:
            return default

        return {**default, **self.options}

    def get_model_call_params(self, node_settings: AIModelNodeSettings, previous_node_outputs=None):
        # Prompt
        prompt = self.settings_override.prompt if self.settings_override.prompt else node_settings.prompt
        if prompt is None:
            raise ValueError("Failed to get prompt as it is not set on node or passed via NodeInput")

        system_instructions = (
            self.system_instructions
            if self.settings_override.system_instructions is not None
            else node_settings.system_instructions
        )
        if system_instructions is None:
            raise ValueError("Failed to get system_instructions as it is not set on node or passed via NodeInput")

        model_call_config = (
            self.settings_override.model_call_config is not None
            if self.settings_override.model_call_config
            else node_settings.model_call_config
        )
        if model_call_config is None:
            raise ValueError("Failed to get model_call_config as it is not set on node or passed via NodeInput")

        # TODO: Complete
        def _get_context(self, previous_node_outputs=None) -> list | None:
            out_context = []
            if self.context:
                out_context.extend(self.context.format())

            if self.context_sources:
                # TODO
                pass
            return out_context

        def _get_options(self, user_options: dict[str, Any] | None = None) -> dict[str, Any]:
            """Returns the merged options dictionary.

            Args:
                user_options: Optional user provided options to merge with overrides

            Returns:
                dict[str, Any]: Merged options with overrides taking precedence
            """
            options = self.call_config.options if self.call_config else {}

            if user_options is None:
                return options

            if options:
                merged = user_options.copy()
                merged.update(options)
                return merged

            return user_options
