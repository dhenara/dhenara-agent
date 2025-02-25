from typing import TypeVar

from dhenara.ai.types.genai.dhenara import AIModelCallResponse
from dhenara.ai.types.shared.base import BaseModel
from pydantic import Field

# -----------------------------------------------------------------------------
T = TypeVar("T", bound=BaseModel)


# -----------------------------------------------------------------------------
class AIModelCallNodeOutputData(BaseModel):
    """
    Base Output model for execution nodes.

    """

    response: AIModelCallResponse | None = Field(
        ...,
        description="External Api call Response or None",
    )
