from typing import Any

from dhenara.types.base import BaseModel
from dhenara.types.flow import FlowExecutionResults, FlowExecutionStatusEnum, FlowNodeInput
from dhenara.types.functional_types.dhenara import AIModelCallNodeOutputData
from pydantic import Field


# -----------------------------------------------------------------------------
class ExecuteDhenRunEndpointReq(BaseModel):
    refnum: str | None = Field(
        ...,
        description="Reference Number of run-endpoint",
    )

    input: FlowNodeInput = Field(
        ...,
        description="Input for starting node",
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

    execution_status: FlowExecutionStatusEnum
    execution_results: FlowExecutionResults[AIModelCallNodeOutputData] = {}
    metadata: dict[str, Any] = {}
