from pydantic import Field

from dhenara.agent.dsl.base import NodeOutcome, NodeOutput
from dhenara.ai.types.shared.base import BaseModel


class OperationResult(BaseModel):
    """Result of a single file operation."""

    type: str
    path: str
    success: bool
    error: str | None = None


class FileOperationNodeOutputData(BaseModel):
    """Output data for the File Operation Node."""

    success: bool
    operations_count: int
    results: list[OperationResult]
    error: str | None = None


class FileOperationNodeOutput(NodeOutput[FileOperationNodeOutputData]):
    pass


class FileOperationNodeOutcome(NodeOutcome):
    """Outcome for the File Operation Node."""

    success: bool = Field(default=False)
    operations_count: int = Field(default=0)
    successful_operations: int = Field(default=0)
    failed_operations: int = Field(default=0)
    errors: list[str] = Field(default_factory=list)
