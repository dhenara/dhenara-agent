
from dhenara.types.base import BaseModel
from dhenara.types.flow import FlowNodeInput
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
    status: str = Field(
        ...,
        description="Unique identifier for the endpoint",
    )
