from pydantic import Field

from dhenara.agent.dsl.base import NodeOutcome, NodeOutput
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import DirectoryInfo, FileInfo
from dhenara.agent.types.base import BaseModel


class FolderAnalysisOperationResult(BaseModel):
    """Result of a single folder analysis operation."""

    operation_type: str = Field(..., description="Type of operation performed")
    path: str | list[str] = Field(..., description="Path(s) of the folder/file analyzed")
    success: bool = Field(..., description="Whether the operation succeeded")
    errors: list[str] | None = Field(default=None)

    # Different result fields based on operation type
    analysis: DirectoryInfo | list[DirectoryInfo] | None = Field(
        default=None, description="Analysis results for folder analysis"
    )
    file_info: FileInfo | list[FileInfo] | None = Field(default=None, description="File info for file analysis")
    files_found: list[str] | None = Field(default=None, description="List of files found by find_files operation")
    tree_diagram: str | None = Field(default=None, description="Tree diagram of folder structure")

    # Stats
    words_read: int | None = Field(default=None, description="Total words read from the file/dir")


class FolderAnalyzerNodeOutputData(BaseModel):
    """Output data for the Folder Analyzer Node."""

    base_directory: str | None = Field(default=None, description="base directory operated on")
    success: bool = Field(default=False)
    errors: list[str] = Field(default_factory=list)

    # New fields for multi-operation support
    operations_count: int = Field(default=0, description="Number of operations executed")
    successful_operations: int = Field(default=0, description="Number of successful operations")
    failed_operations: int = Field(default=0, description="Number of failed operations")

    # Stats
    total_files: int | None = Field(default=None, description="Total files analyzed in base_directory")
    total_directories: int | None = Field(default=None, description="Total directories analyzed in base_directory")
    total_size: int | None = Field(default=None, description="Total size of analyzed items in base_directory")
    word_count: int | None = Field(default=None, description="Total words in the file/dir in base_directory")
    words_read: int | None = Field(default=None, description="Total words read from the base_directory")
    file_types: dict[str, int] = Field(
        default_factory=dict, description="Type of files and their count in base_directory"
    )
    gitignore_patterns: list[str] | None = Field(default=None, description="gitignore patterns in base_directory")


class FolderAnalyzerNodeOutput(NodeOutput[FolderAnalyzerNodeOutputData]):
    """Node output wrapper class."""

    pass


class FolderAnalyzerNodeOutcome(NodeOutcome):
    base_directory: str | None = Field(default=None, description="base directory operated on")
    results: list[FolderAnalysisOperationResult] | None = Field(default=None)
