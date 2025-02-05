# flow_types.py
from datetime import datetime
from typing import Any

from dhenara.types.base import BaseModel
from dhenara.types.flow import FlowDefinition, FlowExecutionStatusEnum, FlowNodeExecutionStatusEnum, FlowNodeIdentifier, FlowNodeInput, FlowNodeOutput, StorageEntityTypeEnum, UserInput

StorageEntityDBData = list[str]  # list of strings


# -----------------------------------------------------------------------------
class FlowNodeExecutionResult(BaseModel):
    node_identifier: FlowNodeIdentifier
    status: FlowNodeExecutionStatusEnum
    user_inputs: list[UserInput]
    node_output: FlowNodeOutput
    storage_data: dict[StorageEntityTypeEnum, StorageEntityDBData]
    created_at: datetime


# -----------------------------------------------------------------------------
class FlowContext(BaseModel):
    endpoint_id: str
    flow_definition: FlowDefinition
    initial_input: FlowNodeInput
    execution_status: FlowExecutionStatusEnum = FlowExecutionStatusEnum.PENDING
    current_node_index: int = 0
    # execution_results: list[FlowNodeExecutionResult] = []
    execution_results: dict[FlowNodeIdentifier, FlowNodeExecutionResult] = []
    # final_output: FlowNodeOutput : Not reuired as it can be found from execution_results
    metadata: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
