from typing import Literal

from pydantic import Field

from dhenara.agent.dsl.base import NodeSettings


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
        default=False,
        description="Whether to include file/dir stats",
    )

    respect_gitignore: bool = Field(
        default=True,
        description="Whether to respect .gitignore patterns",
    )
    max_file_size: int | None = Field(
        default=1024 * 1024,  # 1MB default max for content preview
        description="Maximum file size to analyze content",
    )

    # Content Read related
    read_content: bool = Field(
        default=False,
        description="Whether to read and include the file content.",
    )
    include_content_preview: bool = Field(
        default=False,
        description="Whether to include file content previews",
    )
    # Content optimization options
    content_read_mode: Literal["full", "structure"] = Field(  # "smart_chunks", # TODO_FUTURE
        default="full",
        description="How to process file content",
    )
    content_structure_detail_level: Literal["basic", "standard", "detailed", "full"] = Field(
        default="basic",
        description="DetailLevel if content_read_mode is `structure`",
    )
    max_words_per_file: int | None = Field(
        default=None,
        description="Maximum number of words to include per file when reading content.Set None for unlimitted words",
        ge=0,
    )
    max_total_words: int | None = Field(
        default=None,
        description="Maximum total number of words to include across all files.Set None for unlimitted words",
        ge=0,
    )
    generate_file_summary: bool = Field(
        default=False,
        description="Whether to generate a summary for each file",
    )

    # Path format options
    use_relative_paths: bool = Field(
        default=True,
        description="Whether to use paths relative to the root directory",
    )
    include_root_in_path: bool = Field(
        default=False,
        description="Whether to include the root directory in paths",
    )

    # Tree diagram options
    generate_tree_diagram: bool = Field(
        default=False,
        description="Whether to generate a tree diagram of the directory structure",
    )
    tree_diagram_max_depth: int | None = Field(
        default=None,
        description="Maximum depth for the tree diagram",
    )
    tree_diagram_include_files: bool = Field(
        default=True,
        description="Whether to include files in the tree diagram",
    )
