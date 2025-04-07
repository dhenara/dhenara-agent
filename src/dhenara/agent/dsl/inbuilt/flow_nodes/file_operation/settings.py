# dhenara/agent/dsl/inbuilt/flow_nodes/file_operation/settings.py

from pydantic import Field, field_validator

from dhenara.agent.dsl.base import NodeSettings
from dhenara.agent.dsl.inbuilt.flow_nodes.file_operation.types.file_operation import FileOperation
from dhenara.ai.types.genai.dhenara.request.data import ObjectTemplate


class FileOperationNodeSettings(NodeSettings):
    """Configuration for file operation options."""

    # Directory settings
    base_directory: str = Field(
        ".",
        description="Base directory for file operations",
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
    sequential_processing: bool = Field(
        default=False, description="Re-read file after each modification to support sequential changes"
    )

    # Match options
    fuzzy_matching: bool = Field(
        default=False, description="Use fuzzy matching for finding modification points when exact matches fail"
    )  # TODO: Delete
    fuzzy_match_threshold: float = Field(
        default=0.8,
        description="Threshold for fuzzy matching (0.0-1.0, where 1.0 is exact match)",
        ge=0.0,
        le=1.0,
    )  # TODO: Delete
    allow_regex_matching: bool = Field(
        default=False, description="Allow regex patterns in start_point_match and end_point_match"
    )  # TODO: Delete

    # Error handling
    show_context_on_error: bool = Field(
        default=True, description="Include file context in error messages when matches fail"
    )  # TODO: Delete
    context_lines: int = Field(
        default=3,
        description="Number of context lines to show before and after failed matches",
        ge=0,
    )  # TODO: Delete

    fail_fast: bool = Field(
        default=False,
        description="Stop processing on first failure if True, otherwise continue with remaining operations",
    )

    # Output formatting
    return_diff_format: bool = Field(
        default=True, description="Return git-style diff for file modifications to show changes clearly"
    )
    preserve_indentation: bool = Field(
        default=True, description="Preserve existing code indentation when making modifications"
    )

    @field_validator("fuzzy_match_threshold")
    @classmethod
    def validate_threshold(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("fuzzy_match_threshold must be between 0.0 and 1.0")
        return v
