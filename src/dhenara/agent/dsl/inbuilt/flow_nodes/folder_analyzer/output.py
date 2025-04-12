from pydantic import Field

from dhenara.agent.dsl.base import NodeOutcome
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import DirectoryInfo, FileInfo
from dhenara.ai.types.shared.base import BaseModel


class FolderAnalysisOperationResult(BaseModel):
    """Result of a single folder analysis operation."""

    operation_type: str = Field(..., description="Type of operation performed")
    path: str = Field(..., description="Path of the folder/file analyzed")
    success: bool = Field(..., description="Whether the operation succeeded")
    error: str | None = Field(None, description="Error message if operation failed")

    # Different result fields based on operation type
    analysis: DirectoryInfo | None = Field(None, description="Analysis results for folder analysis")
    file_info: FileInfo | None = Field(None, description="File info for file analysis")
    files_found: list[str] | None = Field(None, description="List of files found by find_files operation")
    tree_diagram: str | None = Field(None, description="Tree diagram of folder structure")

    # Stats
    total_files: int | None = Field(None, description="Total files analyzed")
    total_directories: int | None = Field(None, description="Total directories analyzed")
    total_size: int | None = Field(None, description="Total size of analyzed items")

    def __str__(self):
        """String representation of the result"""
        if not self.success:
            return f"Operation failed: {self.error}"

        if self.operation_type == "analyze_folder":
            return f"Analyzed folder {self.path}: {self.total_files} files, {self.total_directories} directories"
        elif self.operation_type == "analyze_file":
            return f"Analyzed file {self.path}"
        elif self.operation_type == "find_files":
            return f"Found {len(self.files_found or [])} files in {self.path}"
        elif self.operation_type == "get_structure":
            return f"Retrieved structure of {self.path}"
        else:
            return f"Unknown operation {self.operation_type} on {self.path}"


class FolderAnalyzerNodeOutputData(BaseModel):
    """Output data for the Folder Analyzer Node."""

    base_directory: str | None = Field(None, description="base directory operated on")
    success: bool = Field(default=False)
    errors: list[str] = Field(default_factory=list)
    # analysis: DirectoryInfo | None = None
    # tree_diagram: str | None = Field(default=None, description="ASCII tree diagram of the directory structure")
    total_files: int = Field(default=0)
    total_directories: int = Field(default=0)
    total_size: int = Field(default=0)
    file_types: dict[str, int] = Field(default_factory=dict)
    gitignore_patterns: list[str] | None = Field(default=None)
    total_words_read: int | None = Field(default=None)

    # New fields for multi-operation support
    operations_count: int = Field(default=0, description="Number of operations executed")
    successful_operations: int = Field(default=0, description="Number of successful operations")
    failed_operations: int = Field(default=0, description="Number of failed operations")
    operation_results: list[FolderAnalysisOperationResult] = Field(
        default_factory=list, description="Results of individual operations"
    )


class FolderAnalyzerNodeOutcome(NodeOutcome):
    base_directory: str | None = Field(None, description="base directory operated on")
    results: list[FolderAnalysisOperationResult] | None = None
