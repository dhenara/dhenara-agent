from typing import TypeVar

from pydantic import Field

from dhenara.ai.types.genai.dhenara import AIModelCallResponse
from dhenara.ai.types.shared.base import BaseModel

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
