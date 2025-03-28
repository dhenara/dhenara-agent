# flow_execution.py
from datetime import datetime
from typing import Generic, TypeVar

from dhenara.ai.types.shared.base import BaseModel

from .defs import NodeID
from .enums import ExecutionStatusEnum
from .node_io import NodeInput, NodeOutcome, NodeOutput

# TODO
# TODO
# TODO
# TODO
StorageEntityDBData = list[str]  # list of strings

OutputT = TypeVar("OutputT", bound=BaseModel)


# -----------------------------------------------------------------------------
class NodeExecutionResult(BaseModel, Generic[OutputT]):
    node_identifier: NodeID
    status: ExecutionStatusEnum
    # user_inputs: list[Content] | None
    input: NodeInput | None
    output: NodeOutput[OutputT] | None
    outcome: NodeOutcome | None
    # storage_data: dict[StorageEntityTypeEnum, StorageEntityDBData]
    created_at: datetime


# -----------------------------------------------------------------------------
# NodeExecutionResults = dict[NodeID, NodeExecutionResult[OutputT, OutcomeT]]
