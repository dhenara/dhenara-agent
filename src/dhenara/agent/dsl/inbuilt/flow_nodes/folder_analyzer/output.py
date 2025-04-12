from pydantic import Field

from dhenara.agent.dsl.base import NodeOutcome, NodeOutput
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import DirectoryInfo
from dhenara.ai.types.shared.base import BaseModel


class FolderAnalyzerNodeOutputData(BaseModel):
    """Output data for the Folder Analyzer Node."""

    success: bool
    path: str
    analysis: DirectoryInfo | None = None
    error: str | None = None


class FolderAnalyzerNodeOutput(NodeOutput[FolderAnalyzerNodeOutputData]):
    pass


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
