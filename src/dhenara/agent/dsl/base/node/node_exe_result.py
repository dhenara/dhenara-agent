from datetime import datetime
from typing import Generic

from pydantic import Field

from dhenara.agent.dsl.base import (
    ExecutableTypeEnum,
    ExecutionStatusEnum,
    NodeID,
    NodeInputT,
    NodeOutcomeT,
    NodeOutputT,
)
from dhenara.agent.types.base import BaseModel


class NodeExecutionResult(BaseModel, Generic[NodeInputT, NodeOutputT, NodeOutcomeT]):
    executable_type: ExecutableTypeEnum = Field(...)
    node_identifier: NodeID = Field(...)
    execution_status: ExecutionStatusEnum = Field(...)
    input: NodeInputT | None = Field(default=None)
    output: NodeOutputT | None = Field(default=None)
    outcome: NodeOutcomeT | None = Field(default=None)
    error: str | None = Field(default=None)
    errors: list[str] | None = Field(default=None)
    created_at: datetime = Field(...)

    # --- Usage / Cost (only populated for AI Model Call nodes currently) ---
    usage_cost: float | None = Field(
        default=None,
        description="Raw API cost for this node (USD).",
    )
    usage_charge: float | None = Field(
        default=None,
        description="Charge after applying internal margins (USD).",
    )
    usage_prompt_tokens: int | None = Field(default=None, description="Prompt tokens used")
    usage_completion_tokens: int | None = Field(default=None, description="Completion tokens used")
    usage_total_tokens: int | None = Field(default=None, description="Total tokens used")
