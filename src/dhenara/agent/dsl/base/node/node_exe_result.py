from datetime import datetime
from typing import Generic

from dhenara.agent.dsl.base import ExecutionStatusEnum, NodeID, NodeInputT, NodeOutcomeT, NodeOutputT
from dhenara.ai.types.shared.base import BaseModel


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
