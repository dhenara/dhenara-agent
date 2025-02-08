from typing import TypeVar

from pydantic import Field

from dhenara.types.base import BaseModel
from dhenara.types.external_api import ExternalApiCallStatus
from dhenara.types.flow import FlowNodeOutput
from dhenara.types.functional_types import ChatResponse, ImageResponse

# -----------------------------------------------------------------------------
T = TypeVar("T", bound=BaseModel)


# -----------------------------------------------------------------------------
class ExternalApiCallNodeOutput(FlowNodeOutput):
    """
    Base Output model for execution nodes.

    """

    api_call_response: T | None = Field(
        ...,
        description="External Api call Response or None",
    )
    api_call_status: ExternalApiCallStatus = Field(
        ...,
        description="External Api call Status",
    )


# -----------------------------------------------------------------------------
class AiModelCallNodeOutput(ExternalApiCallNodeOutput[ChatResponse | ImageResponse]):
    """
    Output model for `ai_model_call` and `ai_model_call_stream` nodes

    """

    pass
