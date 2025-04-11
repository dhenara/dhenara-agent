from datetime import datetime
from typing import Any, Generic

from pydantic import Field

from dhenara.agent.dsl.base import ComponentTypeEnum, ExecutionStatusEnum, NodeID
from dhenara.agent.dsl.base.node.node_exe_result import NodeExecutionResult, NodeInputT, NodeOutcomeT, NodeOutputT
from dhenara.ai.types.shared.base import BaseModel


class ComponentExecutionResult(BaseModel, Generic[NodeInputT, NodeOutputT, NodeOutcomeT]):
    component_type: ComponentTypeEnum
    component_id: str
    is_rerun: bool
    start_node_id: str | None

    execution_status: ExecutionStatusEnum
    execution_results: dict[
        NodeID,
        NodeExecutionResult[
            NodeInputT,
            NodeOutputT,
            NodeOutcomeT,
        ],
    ] = Field(default_factory=dict, description="Individual node's execution result")

    error: str | None = None
    errors: list[str] | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)


# -----------------------------------------------------------------------------
# NodeExecutionResults = dict[NodeID, NodeExecutionResult[OutputT, OutcomeT]]
