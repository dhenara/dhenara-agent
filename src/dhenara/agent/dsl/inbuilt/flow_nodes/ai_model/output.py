from pydantic import Field

from dhenara.agent.dsl.base import NodeOutcome
from dhenara.ai.types.genai.dhenara import AIModelCallResponse
from dhenara.ai.types.shared.base import BaseModel
from dhenara.ai.types.shared.file import GenericFile


# -----------------------------------------------------------------------------
class AIModelNodeOutputData(BaseModel):
    """
    Base Output model for execution nodes.

    """

    response: AIModelCallResponse | None = Field(
        ...,
        description="External Api call Response or None",
    )


# -----------------------------------------------------------------------------
class AIModelNodeOutcome(NodeOutcome):
    """
    Base Output model for execution nodes.

    """

    text: str | None = Field(default=None)
    structured: dict | None = Field(default=None)
    file: GenericFile | None = Field(default=None)
    files: list[GenericFile] | None = Field(default=None)

    @property
    def has_any(self):
        return self.text or self.structured or self.file or self.files
