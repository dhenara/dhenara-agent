# flow_types.py
from enum import Enum
from typing import Any

from dhenara.types.base import BaseModel
from dhenara.types.models.flow import FlowDefinition, FlowNodeInput


class FlowExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FlowContext(BaseModel):
    workspace_id: str
    endpoint_id: str
    flow_definition: FlowDefinition
    node_input: FlowNodeInput
    execution_status: FlowExecutionStatus = FlowExecutionStatus.PENDING
    current_node_index: int = 0
    execution_results: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
