from pydantic import Field

from dhenara.agent.dsl.base import NodeSettings
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import FileOperation
from dhenara.ai.types.genai.dhenara.request.data import ObjectTemplate, TextTemplate


class FileOperationNodeSettings(NodeSettings):
    """Configuration for file operation options."""

    # Directory settings
    base_directory: str = Field(
        default=".",
        description="Base directory for file operations",
    )
    use_relative_paths: bool = Field(
        default=True,
        description="Whether to use paths relative to the base directory",
    )
    allowed_directories: list[str] = Field(
        default_factory=list,
        description=(
            "List of directories (inside base_directory) that are allowed to be accessed (for security). "
            "Leave empty for allowing all inside base_directoryr"
        ),
    )
    # Operations
    operations: list[FileOperation] = Field(
        default_factory=list,
        description="List of file operations to perform",
    )
    operations_template: ObjectTemplate | None = Field(
        default=None,
        description=(
            "Template to extract file operations from previous node results. "
            "This should resolve to a list of FileOperation objects."
        ),
    )
    # Processing options
    fail_fast: bool = Field(
        default=False,
        description="Stop processing on first failure if True, otherwise continue with remaining operations",
    )
    # Output formatting
    return_diff_format: bool = Field(
        default=True,
        description="Return git-style diff for file modifications to show changes clearly",
    )
    preserve_indentation: bool = Field(
        default=True,
        description="Preserve existing code indentation when making modifications",
    )
    # Git settings
    stage: bool = Field(
        default=False,
        description="Stage the operation results or not. The result path should be a git repo.",
    )
    commit: bool = Field(
        default=False,
        description="Commit the operation results or not.The result path should be a git repo.",
    )
    commit_message: str | TextTemplate | None = Field(
        default=None,
        description="Commot messag",
    )
    # TODO_FUTURE: branch name
