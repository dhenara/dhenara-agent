from pydantic import Field

from dhenara.agent.dsl.base import NodeSettings
from dhenara.agent.types.base import BaseModel


class FileOperation(BaseModel):
    """Represents a single file operation"""

    type: str = Field(..., description="Operation type: create_directory, create_file, modify_file, delete")
    path: str = Field(..., description="Path to the file or directory")
    content: str | None = Field(None, description="Content for file operations")


class FileOperationNodeSettings(NodeSettings):
    """Configuration for file operation options."""

    base_directory: str = Field(".", description="Base directory for file operations")
    operations: list[FileOperation] = Field(default_factory=list, description="List of file operations to perform")
