from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, Generic, NewType, TypeVar

from pydantic import Field

from dhenara.agent.types.data import Content
from dhenara.agent.types.flow import ExecutionStatusEnum
from dhenara.ai.types import ResourceConfigItem
from dhenara.ai.types.shared.base import BaseModel

NodeID = NewType("NodeID", str)
FlowIdentifier = NewType("FlowIdentifier", str)


class NodeInput(BaseModel):  # TODO: Rename to NodeInput
    """
    Input model for execution nodes with validation rules
    """

    content: Content | None = Field(
        None,
        description="Input content",
    )

    # Replacement for prompt variables
    # prompt_vars
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Variables for template resolution",
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
    # Context from other nodes
    context: dict[str, Any] = Field(default_factory=dict, description="Context from previous nodes")

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


# -----------------------------------------------------------------------------
#  Custom Dict Subclass with Type Validation
class NodeInputs(dict[NodeID, NodeInput]):  # TODO: Rename to NodeInputs
    """Dictionary of flow node inputs with type validation."""

    def __setitem__(self, key: NodeID, value: NodeInput) -> None:
        # Optional validation when items are set
        if not isinstance(value, NodeInput):
            raise TypeError(f"Value must be NodeInput, got {type(value)}")
        super().__setitem__(key, value)


# NodeInputs = dict[NodeID, NodeInput]


# -----------------------------------------------------------------------------
# Instead of inheritance, use type alias
FlowNodeExecutionStatusEnum = ExecutionStatusEnum


T = TypeVar("T", bound=BaseModel)


# -----------------------------------------------------------------------------
class OutputEvent(BaseModel):
    """Event generated during node execution"""

    event_type: str  # notification, completion, error, etc.
    payload: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class FlowNodeOutput(BaseModel, Generic[T]):  # rename to NodeOutput
    # Primary output content
    data: T

    # Metadata about the execution
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Events generated during execution
    events: list[OutputEvent] = Field(default_factory=list)

    # Stream reference (if streaming)
    stream: AsyncGenerator | None = None
