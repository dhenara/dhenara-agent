from pydantic import Field

from dhenara.agent.dsl.base import NodeOutcome, NodeOutput
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import FileMetadata
from dhenara.agent.types.base import BaseModel


class OperationResult(BaseModel):
    """Result of a single file operation."""

    type: str = Field(..., description="Type of operation performed")
    path: str | None = Field(None, description="Path of the file/directory operated on")
    success: bool = Field(..., description="Whether the operation succeeded")
    error: str | None = Field(None, description="Error message if operation failed")
    content: str | None = Field(None, description="Content of file for read operations")
    file_metadata: FileMetadata | None = Field(None, description="File metadata for info operations")
    diff: str | None = Field(None, description="Git-style diff showing changes made")
    files: list[str] | None = Field(None, description="List of files for directory operations")


class FileOperationNodeOutputData(BaseModel):
    """Output data for the File Operation Node."""

    base_directory: str | None = Field(None, description="base directory operated on")
    success: bool = Field(..., description="Whether all operations succeeded")
    errors: list[str] = Field(default_factory=list)
    operations_count: int = Field(..., description="Number of operations attempted")
    successful_operations: int = Field(default=0, description="Number of successful operations")
    failed_operations: int = Field(default=0, description="Number of failed operations")


class FileOperationNodeOutput(NodeOutput[FileOperationNodeOutputData]):
    """Node output wrapper class."""

    pass


class FileOperationNodeOutcome(NodeOutcome):
    """Outcome for the File Operation Node."""

    base_directory: str | None = Field(None, description="base directory operated on")
    results: list[OperationResult] = Field(..., description="Results of individual operations")
