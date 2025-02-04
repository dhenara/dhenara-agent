from typing import Any

from dhenara.types.base import BaseModel
from dhenara.types.flow import FlowExecutionStatusEnum, FlowNodeExecutionResult, FlowNodeInput
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
    execution_status: FlowExecutionStatusEnum
    execution_results: list[FlowNodeExecutionResult] = []
    metadata: dict[str, Any] = {}
