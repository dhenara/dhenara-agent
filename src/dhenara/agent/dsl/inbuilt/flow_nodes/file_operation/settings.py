from pydantic import Field

from dhenara.agent.dsl.base import NodeSettings
from dhenara.agent.dsl.inbuilt.flow_nodes.file_operation.types import FileOperation
from dhenara.ai.types.genai.dhenara.request.data import TextTemplate


class FileOperationNodeSettings(NodeSettings):
    """Configuration for file operation options."""

    base_directory: str = Field(
        ".",
        description="Base directory for file operations",
    )
    operations: list[FileOperation] = Field(
        default_factory=list,
        description="List of file operations to perform",
    )
    operations_template: TextTemplate | None = Field(
        default=None,
        description=(
            "Template to extract file operations from previous node results. "
            "This should resolve to a list of FileOperation objects."
        ),
    )
