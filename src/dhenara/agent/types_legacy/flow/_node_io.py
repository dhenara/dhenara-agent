from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, Generic, NewType, TypeVar

from pydantic import Field

from dhenara.agent.types.flow import ExecutionStatusEnum
from dhenara.ai.types.shared.base import BaseModel

LegacyNodeID = NewType("NodeID", str)
LegacyFlowIdentifier = NewType("FlowIdentifier", str)


class LegacyNodeInput(BaseModel):  # TODO: Rename to AINodeInput
    settings_override: None


# -----------------------------------------------------------------------------
#  Custom Dict Subclass with Type Validation
class LegacyNodeInputs(dict[LegacyNodeID, LegacyNodeInput]):  # TODO: Rename to NodeInputs
    """Dictionary of flow node inputs with type validation."""

    def __setitem__(self, key: LegacyNodeID, value: LegacyNodeInput) -> None:
        # Optional validation when items are set
        if not isinstance(value, LegacyNodeInput):
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


class LegacyFlowNodeOutput(BaseModel, Generic[T]):  # rename to NodeOutput
    # Primary output content
    data: T

    # Metadata about the execution
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Events generated during execution
    events: list[OutputEvent] = Field(default_factory=list)

    # Stream reference (if streaming)
    stream: AsyncGenerator | None = None
