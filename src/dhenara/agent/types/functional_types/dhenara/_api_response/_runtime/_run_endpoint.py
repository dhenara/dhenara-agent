from typing import Any

from pydantic import Field

from dhenara.agent.types.flow import ExecutionResults, ExecutionStatusEnum, NodeID, NodeInput
from dhenara.agent.types.functional_types.dhenara import AIModelCallNodeOutputData
from dhenara.ai.types.shared.base import BaseModel


# -----------------------------------------------------------------------------
class ExecuteDhenRunEndpointReq(BaseModel):
    refnum: str | None = Field(
        ...,
        description="Reference Number of run-endpoint",
    )

    initial_inputs: dict[NodeID, NodeInput] = Field(
        ...,
        description="Initial inputs for nodes",
    )


# -----------------------------------------------------------------------------


class ExecuteDhenRunEndpointRes(BaseModel):
    """
    Represents the response from executing a Dhen run endpoint.

    Attributes:
        execution_status: Status of the execution
        execution_results: Dictionary of node execution results specifically for AI model calls
        metadata: Additional metadata about the execution
    """

    execution_status: ExecutionStatusEnum
    execution_results: ExecutionResults[AIModelCallNodeOutputData] = {}
    metadata: dict[str, Any] = {}
