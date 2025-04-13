from typing import Any, Literal

from pydantic import BaseModel, Field

from .file_operation import FileMetadata


class FileInfo(BaseModel):
    """Information about a file."""

    type: Literal["file"] = Field(default="file", description="Type of the object")
    name: str = Field(..., description="Name of the file")
    path: str = Field(..., description="Path to the file")
    extension: str = Field(default="", description="File extension")

    content_preview: str | None = Field(default=None, description="Preview of the file content")
    content: str | None = Field(default=None, description="Full content of the file")
    # Currently content_structure read is only supported for python files
    content_structure: str | None = Field(default=None, description="Structure of the content (e.g., for Python files)")

    metadata: FileMetadata | None = Field(default=None, description="File Metadata")

    error: str | None = Field(default=None, description="Error message, if any")
    word_count: int | None = Field(default=None, description="Word count of the file")
    is_text: bool | None = Field(default=None, description="Whether the file is a text file")
    mime_type: str | None = Field(default=None, description="MIME type of the file")
    summary: str | None = Field(default=None, description="Summary of the file content")

    def get_with_content_fields(self) -> dict:
        """Select minimum set of fields related to contents.
        This can be used to give context to LLM for passing content."""

        exclude_fields = ["metadata", "is_text", "mime_type", "summary"]
        if self.content:
            exclude_fields.extend(["content_preview", "content_structure"])
        elif self.content_structure:
            exclude_fields.extend(["content_preview", "content"])

        return self.model_dump(exclude=exclude_fields)


class DirectoryInfo(BaseModel):
    """Information about a directory."""

    type: Literal["directory"] = Field(default="directory", description="Type of the object")
    name: str = Field(..., description="Name of the directory")
    path: str = Field(..., description="Path to the directory")
    children: list[Any] = Field(default_factory=list, description="List of children. Can be FileInfo or DirectoryInfo")
    file_count: int = Field(default=0, description="Number of files in the directory")
    dir_count: int = Field(default=0, description="Number of subdirectories in the directory")
    truncated: bool = Field(default=False, description="Whether the directory listing was truncated")
    # Dir metadata fields
    size: int | None = Field(default=None, description="Size of the directory in bytes")
    created: str | None = Field(default=None, description="Creation timestamp")
    modified: str | None = Field(default=None, description="Last modification timestamp")
    accessed: str | None = Field(default=None, description="Last accessed timestamp")
    permissions: str | None = Field(default=None, description="File permissions in octal format")

    errors: list[str] = Field(
        default_factory=list, description="Error messages of failed reads ( could be multiple for a dir"
    )
    word_count: int = Field(default=0, description="Total words in the file/dir")
    file_types: dict[str, int] = Field(default_factory=dict, description="Type of files and their count in dir")
    total_files: int = Field(default=0, description="Total files analyzed")
    total_directories: int = Field(default=0, description="Total directories analyzed")
    total_size: int = Field(default=0, description="Total size of analyzed items")
    gitignore_patterns: list[str] = Field(default_factory=list, description="gitignore patterns in dir")


class FolderAnalysisOperation(BaseModel):
    """Defines a folder analysis operation"""

    # Operation type
    operation_type: Literal[
        "analyze_folder",
        "analyze_file",
        "find_files",
        "get_structure",
    ] = Field(..., description="Type of folder analysis operation to perform")

    # Path specification
    path: str = Field(
        ...,
        description="Path to the folder or file to analyze",
    )

    include_root_in_path: bool = Field(
        default=False,
        description="Whether to include the root directory in paths",
    )

    # Traversal and filtering options
    max_depth: int | None = Field(default=None, description="Maximum depth to traverse for folder analysis", ge=0)
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns of files/dirs to exclude (glob format)",
    )
    include_hidden: bool = Field(
        default=False,
        description="Whether to include hidden files/folders",
    )
    respect_gitignore: bool = Field(
        default=True,
        description="Whether to respect .gitignore patterns",
    )

    # Content reading options
    read_content: bool = Field(
        default=False,
        description="Whether to read file content",
    )
    include_content_preview: bool = Field(
        default=False,
        description="Whether to include file content previews",
    )
    content_read_mode: Literal["full", "structure"] = Field(
        default="full",
        description="How to process file content",
    )
    content_structure_detail_level: Literal["basic", "standard", "detailed", "full"] = Field(
        default="basic",
        description="Detail level if content_read_mode is `structure`",
    )

    # Size and content limits
    max_file_size: int | None = Field(
        default=1024 * 1024,  # 1MB default
        description="Maximum file size to analyze content",
    )
    max_words_per_file: int | None = Field(
        default=None,
        description="Maximum number of words per file when reading content",
        ge=0,
    )
    max_total_words: int | None = Field(
        default=None,
        description="Maximum total number of words to include across all files",
        ge=0,
    )

    # Analysis and display options
    include_stats: bool = Field(
        default=False,
        description="Whether to include file/dir stats",
    )
    generate_file_summary: bool = Field(
        default=False,
        description="Whether to generate a summary for each file",
    )
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

    def validate_content_type(self) -> bool:
        """Validates that the parameters are valid for this operation type"""
        if self.operation_type in ["analyze_folder", "analyze_file", "find_files", "get_structure"] and not self.path:
            return False
        return True
