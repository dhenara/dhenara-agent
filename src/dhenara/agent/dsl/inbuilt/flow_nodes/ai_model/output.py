from pydantic import Field

from dhenara.agent.dsl.base import NodeOutcome, NodeOutput
from dhenara.agent.types.base import BaseModel
from dhenara.ai.types.genai.dhenara import AIModelCallResponse
from dhenara.ai.types.shared.file import StoredFile


class AIModelNodeOutputData(BaseModel):
    response: AIModelCallResponse | None = Field(
        ...,
        description="External Api call Response",
    )


class AIModelNodeOutput(NodeOutput[AIModelNodeOutputData]):
    pass


class AIModelNodeOutcome(NodeOutcome):
    text: str | None = Field(default=None)
    structured: dict | None = Field(default=None)
    files: list[StoredFile] | None = Field(default=None)

    @property
    def has_any(self):
        return self.text or self.structured or self.file or self.files
