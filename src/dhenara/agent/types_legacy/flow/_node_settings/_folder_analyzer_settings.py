from pydantic import Field, model_validator

from dhenara.agent.types.data import RunEnvParams
from dhenara.ai.types.shared.base import BaseModel


class FolderAnalyzerSettings(BaseModel):
    """Settings for folder analyzer execution nodes.

    Attributes:
        path: Path to the folder to analyze
        max_depth: Maximum depth to traverse (None for unlimited)
        exclude_patterns: Glob patterns to exclude from analysis
        include_hidden: Whether to include hidden files (starting with .)
        include_stats: Whether to include file statistics (size, date, etc.)
        include_content: Whether to analyze content types (e.g., detect text, binary)
        max_file_size: Maximum file size in bytes to read content from (None for unlimited)
    """

    path: str = Field(
        ...,
        description="Path to the folder to analyze",
    )
    max_depth: int | None = Field(
        default=None,
        description="Maximum depth to traverse (None for unlimited)",
        ge=1,
    )
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [".git", "__pycache__", "*.pyc", "*.pyo", "*.pyd", "*.so", "*.dll"],
        description="Glob patterns to exclude from analysis",
    )
    include_hidden: bool = Field(
        default=False,
        description="Whether to include hidden files (starting with .)",
    )
    include_stats: bool = Field(
        default=True,
        description="Whether to include file statistics (size, date, etc.)",
    )
    include_content: bool = Field(
        default=False,
        description="Whether to analyze content types (e.g., detect text, binary)",
    )
    max_file_size: int | None = Field(
        default=1048576,  # 1MB default limit
        description="Maximum file size in bytes to read content from (None for unlimited)",
        ge=0,
    )

    @model_validator(mode="after")
    def validate_path(self) -> "FolderAnalyzerSettings":
        """Validate that path is properly formatted."""
        # This will be checked at runtime, not during model validation
        return self

    def get_formatted_path(self, run_env_params: RunEnvParams) -> tuple[list[str], str]:
        template_vars = run_env_params.get_template_variables()

        if not self.path:
            raise ValueError("get_formatted_path: path is not set")

        try:
            formatted_path = self.path.format(**template_vars)
            return formatted_path
        except Exception as e:
            raise ValueError(f"get_formatted_path: Error for path {self.path}: {e}")


class GitRepoAnalyzerSettings(FolderAnalyzerSettings):
    """Settings for git repository analyzer execution nodes.

    Extends FolderAnalyzerSettings with Git-specific options.

    Attributes:
        include_git_history: Whether to include git commit history
        max_commits: Maximum number of commits to include
        include_branch_info: Whether to include branch information
        branches: List of branches to analyze (None for all)
    """

    include_git_history: bool = Field(
        default=True,
        description="Whether to include git commit history",
    )
    max_commits: int | None = Field(
        default=50,
        description="Maximum number of commits to include",
        ge=1,
    )
    include_branch_info: bool = Field(
        default=True,
        description="Whether to include branch information",
    )
    branches: list[str] | None = Field(
        default=None,
        description="List of branches to analyze (None for all)",
    )
