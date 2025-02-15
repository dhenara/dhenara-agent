# flow_execution.py
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import Field, RootModel

from dhenara.types.base import BaseModel
from dhenara.types.flow import FlowNodeExecutionStatusEnum, FlowNodeIdentifier, FlowNodeOutput, StorageEntityTypeEnum, UserInput

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


class FlowExecutionResults(RootModel[T], Generic[T]):
    """
    Represents the execution results of a flow, mapping node identifiers to their execution results.

    This model provides dictionary-like access to execution results while maintaining type safety.

    Attributes:
        root: Dictionary mapping node identifiers to their execution results
    """

    root: dict[FlowNodeIdentifier, FlowNodeExecutionResult[T]] = Field(
        default_factory=dict,
        description="Mapping of node identifiers to their execution results",
    )

    def items(self):
        """Provide dictionary-like items() access to the root dictionary."""
        return self.root.items()

    def __getitem__(self, key: str) -> "FlowNodeExecutionResult[T]":
        """Enable dictionary-like access to results."""
        return self.root[key]

    def __iter__(self):
        """Enable iteration over the root dictionary."""
        return iter(self.root)


''' TODO: Delete
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
'''


#
