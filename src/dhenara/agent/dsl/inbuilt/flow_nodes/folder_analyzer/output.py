from typing import Any

from pydantic import Field

from dhenara.agent.dsl.base import NodeOutcome
from dhenara.ai.types.shared.base import BaseModel


class FileInfo(BaseModel):
    """Information about a file."""

    type: str = "file"
    name: str
    path: str
    extension: str = ""
    size: int | None = None
    created: str | None = None
    modified: str | None = None
    mime_type: str | None = None
    is_text: bool | None = None
    content_preview: str | None = None
    content: str | None = None  # full content
    word_count: int | None = None  # word counts
    summary: str | None = None  # file summary
    error: str | None = None


class DirectoryInfo(BaseModel):
    """Information about a directory."""

    type: str = "directory"
    name: str
    path: str
    children: list[Any] = []  # Can be FileInfo or DirectoryInfo
    file_count: int = 0
    dir_count: int = 0
    truncated: bool = False
    size: int | None = None
    created: str | None = None
    modified: str | None = None
    error: str | None = None


class FolderAnalyzerNodeOutputData(BaseModel):
    """Output data for the Folder Analyzer Node."""

    success: bool
    path: str
    analysis: DirectoryInfo | None = None
    error: str | None = None


class FolderAnalyzerNodeOutcome(NodeOutcome):
    """Outcome for the Folder Analyzer Node."""

    success: bool = Field(default=False)
    analysis: DirectoryInfo | None = None
    tree_diagram: str | None = Field(default=None, description="ASCII tree diagram of the directory structure")
    root_path: str | None = Field(default=None, description="Root path for analysis")
    total_files: int = Field(default=0)
    total_directories: int = Field(default=0)
    total_size: int = Field(default=0)
    file_types: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    gitignore_patterns: list[str] | None = Field(default=None)
    total_words_read: int | None = Field(default=None)
