from typing import TypeVar

from pydantic import Field

from dhenara.types.base import BaseModel
from dhenara.types.functional_types.dhenara import AIModelCallResponse

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
