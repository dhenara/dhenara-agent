from pydantic import Field

from dhenara.agent.dsl.base import NodeSettings
from dhenara.agent.dsl.inbuilt.flow_nodes.file_operation.types import FileOperation


class FileOperationNodeSettings(NodeSettings):
    """Configuration for file operation options."""

    base_directory: str = Field(".", description="Base directory for file operations")
    operations: list[FileOperation] = Field(default_factory=list, description="List of file operations to perform")
