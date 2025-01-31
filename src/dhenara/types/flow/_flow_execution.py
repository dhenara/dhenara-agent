# flow_types.py
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from dhenara.types.base import BaseModel
from dhenara.types.flow import FlowDefinition, FlowNodeInput


# -----------------------------------------------------------------------------
class FlowExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# -----------------------------------------------------------------------------
class FlowExecutionResult(BaseModel):
    execution_id: str
    status: FlowExecutionStatus
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
class FlowContext(BaseModel):
    workspace_id: str
    endpoint_id: str
    flow_definition: FlowDefinition
    node_input: FlowNodeInput
    execution_status: FlowExecutionStatus = FlowExecutionStatus.PENDING
    current_node_index: int = 0
    execution_results: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
