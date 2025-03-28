from pydantic import Field

from dhenara.agent.dsl.base import NodeInput

from .settings import FileOperation, FileOperationNodeSettings


class FileOperationNodeInput(NodeInput):
    """Input for the File Operation Node."""

    base_directory: str | None = Field(None, description="Base directory for file operations")
    operations: list[FileOperation] | None = Field(None, description="List of file operations to perform")
    json_operations: str | None = Field(None, description="JSON string of operations")
    settings_override: FileOperationNodeSettings = None
