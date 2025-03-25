# flow_execution.py
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import Field, RootModel

from dhenara.ai.types.shared.base import BaseModel

from .defs import NodeID
from .enums import ExecutionStatusEnum
from .node_io import NodeInput, NodeOutput

# TODO
# TODO
# TODO
# TODO
StorageEntityDBData = list[str]  # list of strings

T = TypeVar("T", bound=BaseModel)


# -----------------------------------------------------------------------------
class NodeExecutionResult(BaseModel, Generic[T]):
    node_identifier: NodeID
    status: ExecutionStatusEnum
    # user_inputs: list[Content] | None
    node_input: NodeInput | None
    node_output: NodeOutput[T]
    # storage_data: dict[StorageEntityTypeEnum, StorageEntityDBData]
    created_at: datetime


# -----------------------------------------------------------------------------


# INFO:
#  Below root model definition is to create an object field like
#  ---      ExecutionResults[T] = dict[NodeID, NodeExecutionResult[Generic[T]]]


class ExecutionResults(RootModel[T], Generic[T]):
    """
    Represents the execution results of a flow, mapping node identifiers to their execution results.

    This model provides dictionary-like access to execution results while maintaining type safety.

    Attributes:
        root: Dictionary mapping node identifiers to their execution results
    """

    root: dict[NodeID, NodeExecutionResult[T]] = Field(
        default_factory=dict,
        description="Mapping of node identifiers to their execution results",
    )

    def items(self):
        """Provide dictionary-like items() access to the root dictionary."""
        return self.root.items()

    def __getitem__(self, key: str) -> "NodeExecutionResult[T]":
        """Enable dictionary-like access to results."""
        return self.root[key]

    def __iter__(self):
        """Enable iteration over the root dictionary."""
        return iter(self.root)


''' TODO: Delete
class ExecutionResults(RootModel[T]):  # Note: RootModel
    """
    Represents the execution results of a flow, mapping node identifiers to their execution results.

    Attributes:
        __root__: A dictionary mapping NodeID to NodeExecutionResult of type T.
    """

    root: dict[NodeID, NodeExecutionResult[T]] = Field(
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
