from typing import Any, Generic, TypeVar

from pydantic import Field

from dhenara.agent.types.data import Content
from dhenara.agent.types.flow import FlowExecutionStatusEnum
from dhenara.ai.types import ResourceConfigItem
from dhenara.ai.types.shared.base import BaseModel


class FlowNodeInput(BaseModel):
    """
    Input model for execution nodes with validation rules
    """

    content: Content = Field(
        ...,
        description="Input content",
    )

    # Replacement for prompt variables
    prompt_vars: dict = Field(
        default_factory=dict,
        description="Prompt Variable with thier values",
        example={"style": "modern", "name": "Annie"},
    )

    # Resouce overrides
    resources: list[ResourceConfigItem] = Field(
        default_factory=list,
        description="List of resources to be used",
    )

    # AIModel Options overrides
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration options for the AI model behavior",
        example={
            "temperature": 0.7,
            "max_output_tokens": 100,
            "top_p": 1.0,
        },
    )

    # NOTE:
    # `is_default` validations for resoures are added inside flow models,
    # note input models

    # @model_validator(mode="after")
    # def validate_action_requirements(self) -> "FlowNodeInput":
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


# -----------------------------------------------------------------------------
# Instead of inheritance, use type alias
FlowNodeExecutionStatusEnum = FlowExecutionStatusEnum


T = TypeVar("T", bound=BaseModel)


# -----------------------------------------------------------------------------
class FlowNodeOutput(BaseModel, Generic[T]):
    """
    Base Output model for execution nodes.

    """

    data: T = Field(
        ...,
        description="Data",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the execution",
    )
