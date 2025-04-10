from datetime import datetime
from typing import Generic, TypeVar

from dhenara.agent.dsl.base import ExecutionStatusEnum, NodeID
from dhenara.ai.types.shared.base import BaseModel

NodeInputT = TypeVar("NodeInputT", bound=BaseModel)
NodeOutputT = TypeVar("NodeOutputT", bound=BaseModel)
NodeOutcomeT = TypeVar("NodeOutcomeT", bound=BaseModel)


class NodeExecutionResult(BaseModel, Generic[NodeInputT, NodeOutputT, NodeOutcomeT]):
    node_identifier: NodeID
    status: ExecutionStatusEnum
    input: NodeInputT | None
    output: NodeOutputT | None
    outcome: NodeOutcomeT | None
    error: str | None = None
    errors: list[str] | None = None
    created_at: datetime


# -----------------------------------------------------------------------------
# NodeExecutionResults = dict[NodeID, NodeExecutionResult[OutputT, OutcomeT]]
