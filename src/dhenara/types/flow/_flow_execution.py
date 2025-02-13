# flow_execution.py
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import Field, RootModel

from dhenara.types.base import BaseModel
from dhenara.types.flow import FlowDefinition, FlowExecutionStatusEnum, FlowNodeExecutionStatusEnum, FlowNodeIdentifier, FlowNodeInput, FlowNodeOutput, StorageEntityTypeEnum, UserInput

StorageEntityDBData = list[str]  # list of strings

T = TypeVar("T", bound=BaseModel)


# -----------------------------------------------------------------------------
class FlowNodeExecutionResult(BaseModel, Generic[T]):
    node_identifier: FlowNodeIdentifier
    status: FlowNodeExecutionStatusEnum
    user_inputs: list[UserInput]
    node_output: FlowNodeOutput[T]
    storage_data: dict[StorageEntityTypeEnum, StorageEntityDBData]
    created_at: datetime


# -----------------------------------------------------------------------------


# INFO:
#  Below root model definition is to create an object field like
#  ---      FlowExecutionResults[T] = dict[FlowNodeIdentifier, FlowNodeExecutionResult[Generic[T]]]
class FlowExecutionResults(RootModel[T]):  # Note: RootModel
    """
    Represents the execution results of a flow, mapping node identifiers to their execution results.

    Attributes:
        __root__: A dictionary mapping FlowNodeIdentifier to FlowNodeExecutionResult of type T.
    """

    root: dict[FlowNodeIdentifier, FlowNodeExecutionResult[T]] = Field(
        ...,
        description="Mapping of node identifiers to their execution results.",
        example={
            "node_1": {
                "node_identifier": {"id": "node_1"},
                "status": "success",
                "user_inputs": [{"input_key": "param1", "input_value": "value1"}],
                "node_output": {"data": {"result": 42}},
                "storage_data": {"TYPE_A": {"key": "storage_key", "value": "storage_value"}},
                "created_at": "2023-10-01T12:34:56.789Z",
            }
        },
    )


# -----------------------------------------------------------------------------
class FlowContext(BaseModel):
    endpoint_id: str
    flow_definition: FlowDefinition
    initial_input: FlowNodeInput
    execution_status: FlowExecutionStatusEnum = FlowExecutionStatusEnum.PENDING
    current_node_index: int = 0
    execution_results: FlowExecutionResults[Any] = {}
    # final_output: FlowNodeOutput : Not reuired as it can be found from execution_results
    metadata: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
