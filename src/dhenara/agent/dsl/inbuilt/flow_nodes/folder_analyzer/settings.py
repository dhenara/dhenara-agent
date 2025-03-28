from pydantic import Field

from dhenara.agent.dsl.base import NodeSettings
from dhenara.agent.types.data import RunEnvParams


class FolderAnalyzerSettings(NodeSettings):
    """Configuration for folder analyzer options."""

    path: str = Field(..., description="Path to analyze")
    max_depth: int | None = Field(
        default=None,
        description="Maximum depth to traverse",
        ge=0,
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns of files/dirs to exclude (glob format)",
    )
    include_hidden: bool = Field(
        default=False,
        description="Whether to include hidden files/dirs",
    )
    include_stats: bool = Field(
        default=True,
        description="Whether to include file/dir stats",
    )
    include_content: bool = Field(
        default=False,
        description="Whether to include file content previews",
    )
    max_file_size: int | None = Field(
        default=1024 * 1024,  # 1MB default max for content preview
        description="Maximum file size to analyze content",
    )

    def get_formatted_path(self, run_env_params: RunEnvParams) -> str:
        """Format path with variables."""
        variables = run_env_params.get_template_variables()
        path = self.path
        for var_name, var_value in variables.items():
            path = path.replace(f"{{{var_name}}}", str(var_value))
        return path
