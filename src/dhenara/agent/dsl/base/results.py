# flow_execution.py
from datetime import datetime
from typing import Generic, TypeVar

from dhenara.ai.types.shared.base import BaseModel

from .defs import NodeID
from .enums import ExecutionStatusEnum
from .node_io import NodeInput, NodeOutCome, NodeOutput

# TODO
# TODO
# TODO
# TODO
StorageEntityDBData = list[str]  # list of strings

OutputT = TypeVar("OutputT", bound=BaseModel)
OutcomeT = TypeVar("OutcomeT", bound=BaseModel)


# -----------------------------------------------------------------------------
class NodeExecutionResult(BaseModel, Generic[OutputT, OutcomeT]):
    node_identifier: NodeID
    status: ExecutionStatusEnum
    # user_inputs: list[Content] | None
    node_input: NodeInput | None
    node_output: NodeOutput[OutputT]
    node_outcome: NodeOutCome[OutcomeT]
    # storage_data: dict[StorageEntityTypeEnum, StorageEntityDBData]
    created_at: datetime


# -----------------------------------------------------------------------------
# NodeExecutionResults = dict[NodeID, NodeExecutionResult[OutputT, OutcomeT]]
