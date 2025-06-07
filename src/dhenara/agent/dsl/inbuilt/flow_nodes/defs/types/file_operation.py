from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class FileOperationType(Enum):
    # File operations
    create_file = "create_file"
    # For reads, use FolderAnalysizNode with more controls and options
    # read_file = "read_file"
    # read_multiple_files = "read_multiple_files"
    edit_file = "edit_file"
    delete_file = "delete_file"

    # Directory operations
    create_directory = "create_directory"
    delete_directory = "delete_directory"
    list_directory = "list_directory"

    # Navigation operations
    move_file = "move_file"
    search_files = "search_files"
    get_file_metadata = "get_file_metadata"
    list_allowed_directories = "list_allowed_directories"


class SimpleFileOperation(BaseModel):
    """
    Represents a single file operation for the filesystem.
    Supports only creation and deletion types.
    Useful for precise LLM operations, (without edits)
    """

    # Using Literal instead of Enum for better compatibility with structured output
    type: Literal[
        "create_file",
        "delete_file",
        "create_directory",
        "delete_directory",
    ] = Field(
        ...,
        description="Type of file operation to perform",
    )
    path: str | None = Field(
        default=None,
        description="Path to the target file or directory",
    )
    content: str | None = Field(
        default=None,
        description="Content for file creation operations",
    )

    def validate_content_type(self) -> bool:
        """Validates that the content field matches the expected type based on operation type"""
        if self.type == "create_file" and not isinstance(self.content, str):
            return False
        return True


class EditOperation(BaseModel):
    """Advanced edit operation with better pattern matching"""

    old_text: str = Field(
        ...,
        description="Text to search for - must match exactly",
    )
    new_text: str = Field(
        ...,
        description="Text to replace with",
    )


class SearchConfig(BaseModel):
    """Configuration for file search operations"""

    pattern: str = Field(
        ...,
        description="Search pattern to match in filenames",
    )
    exclude_patterns: list[str] | None = Field(
        default_factory=list,
        description="Patterns to exclude from search results (glob format supported)",
    )


class FileMetadata(BaseModel):
    """Information about a file or directory"""

    size: int = Field(..., description="Size in bytes")
    created: str = Field(..., description="Creation timestamp")
    modified: str = Field(..., description="Last modified timestamp")
    accessed: str = Field(..., description="Last accessed timestamp")
    is_directory: bool = Field(..., description="Whether this is a directory")
    is_file: bool = Field(..., description="Whether this is a file")
    permissions: str = Field(..., description="File permissions in octal format")


class FileOperation(SimpleFileOperation):
    """
    Represents a single file operation for the filesystem.
    Extention of SimpleFileOperation with more types supported
    """

    # Using Literal instead of Enum for better compatibility with structured output
    type: Literal[
        "create_file",
        "edit_file",
        "delete_file",
        "create_directory",
        "delete_directory",
        "list_directory",
        "move_file",
        "search_files",
        "get_file_info",
        "list_allowed_directories",
    ] = Field(
        ...,
        description="Type of file operation to perform",
    )
    paths: list[str] | None = Field(
        default=None,
        description="Multiple file paths for operations that work on multiple files",
    )
    edits: list[EditOperation] | None = Field(
        default=None,
        description="List of edits to apply to a file",
    )
    dry_run: bool | None = Field(
        default=False,
        description="Preview changes without applying them",
    )
    source: str | None = Field(
        default=None,
        description="Source path for move operations",
    )
    destination: str | None = Field(
        default=None,
        description="Destination path for move operations",
    )
    search_config: SearchConfig | None = Field(
        default=None,
        description="Configuration for file search operations",
    )

    def validate_content_type(self) -> bool:
        """Validates that the content field matches the expected type based on operation type"""
        if self.type == "create_file" and not isinstance(self.content, str):
            return False
        if self.type == "edit_file" and not self.edits:
            return False
        if self.type == "read_multiple_files" and not self.paths:
            return False
        if self.type == "move_file" and (not self.source or not self.destination):
            return False
        if self.type == "search_files" and not self.search_config:
            return False
        return True
