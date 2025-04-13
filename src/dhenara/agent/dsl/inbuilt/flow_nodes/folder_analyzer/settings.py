from pydantic import Field

from dhenara.agent.dsl.base import NodeSettings
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import FolderAnalysisOperation
from dhenara.ai.types.genai.dhenara.request.data import ObjectTemplate


class FolderAnalyzerSettings(NodeSettings):
    """Configuration for folder analyzer options."""

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
    operations: list[FolderAnalysisOperation] = Field(
        default_factory=list,
        description="List of folder analysis operations to perform",
    )
    operations_template: ObjectTemplate | None = Field(
        default=None,
        description=(
            "Template to extract folder analysis operations from previous node results. "
            "This should resolve to a list of FolderAnalysisOperation objects."
        ),
    )
    # Processing options
    fail_fast: bool = Field(
        default=False,
        description="Stop processing on first failure if True, otherwise continue with remaining operations",
    )
