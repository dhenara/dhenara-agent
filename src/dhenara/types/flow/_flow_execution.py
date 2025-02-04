# flow_types.py
from datetime import datetime
from typing import Any

from dhenara.types.base import BaseModel
from dhenara.types.flow import FlowDefinition, FlowExecutionStatusEnum, FlowNodeExecutionStatusEnum, FlowNodeIdentifier, FlowNodeInput, FlowNodeOutput


# -----------------------------------------------------------------------------
class FlowNodeExecutionResult(BaseModel):
    node_identifier: FlowNodeIdentifier
    status: FlowNodeExecutionStatusEnum
    status_info: Any | None  # TODO: convert dataclass/ai_model
    node_input: FlowNodeInput
    node_output: FlowNodeOutput
    created_at: datetime


# -----------------------------------------------------------------------------
class FlowContext(BaseModel):
    endpoint_id: str
    flow_definition: FlowDefinition
    initial_input: FlowNodeInput
    execution_status: FlowExecutionStatusEnum = FlowExecutionStatusEnum.PENDING
    current_node_index: int = 0
    execution_results: list[FlowNodeExecutionResult] = []
    # final_output: FlowNodeOutput : Not reuired as it can be found from execution_results
    metadata: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
