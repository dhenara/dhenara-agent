from collections.abc import AsyncGenerator
from typing import Any, Generic, TypeVar

from pydantic import Field

from dhenara.agent.dsl.base import NodeID, NodeSettings
from dhenara.ai.types.shared.base import BaseModel


class NodeInput(BaseModel):
    settings_override: NodeSettings


#  Custom Dict Subclass with Type Validation
# NodeInputs = dict[NodeID, NodeInput]
class NodeInputs(dict[NodeID, NodeInput]):
    """Dictionary of node inputs with type validation."""

    def __setitem__(self, key: NodeID, value: NodeInput) -> None:
        # Optional validation when items are set
        if not isinstance(value, NodeInput):
            raise TypeError(f"Value must be NodeInput, got {type(value)}")
        super().__setitem__(key, value)


# TODO: Enable
# class NodeOutputEvent(BaseModel):
#    """Event generated during node execution"""
#
#    event_type: str  # notification, completion, error, etc.
#    payload: dict[str, Any]
#    timestamp: datetime = Field(default_factory=datetime.now)


# TODO:  Add a NodeState model and cleanup the state recording for all models.
# Also add it to ExecutionResult


T = TypeVar("T", bound=BaseModel)


class NodeOutput(BaseModel, Generic[T]):
    # Primary output content
    data: T

    # Metadata about the execution
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Events generated during execution
    # events: list[NodeOutputEvent] = Field(default_factory=list)

    # Stream reference (if streaming)
    stream: AsyncGenerator | None = None


class NodeOutcome(BaseModel):
    pass
