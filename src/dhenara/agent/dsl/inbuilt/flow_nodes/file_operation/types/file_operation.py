# ruff:noqa: E501
from enum import Enum
from typing import Literal

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field


# Note: Use PydanticBaseModel and Enum, as these will be used in .dad definitions
class FileOperationType(Enum):
    create_directory = "create_directory"
    delete_directory = "delete_directory"
    create_file = "create_file"
    modify_file = "modify_file"
    delete_file = "delete_file"


class FileModificationContent(PydanticBaseModel):
    """Content specification for file modification operations"""

    start_point_match: str = Field(..., description="Pattern to identify the starting point for modification")
    end_point_match: str = Field(..., description="Pattern to identify the ending point for modification")
    new_content: str = Field(
        ...,
        description="New content to insert between start and end points. Use empty string to delete content between points.",
    )


class FileOperation(PydanticBaseModel):
    """Represents a single file operation for the filesystem"""

    # INFO:
    # Do no add Emuns ( like FileOperationType) they will cause issues in AIModel structured outputs FileOperationType
    type: Literal[
        "create_directory",
        "delete_directory",
        "create_file",
        "modify_file",
        "delete_file",
    ] = Field(
        ...,
        description="Type of file operation to perform",
    )
    path: str = Field(..., description="Path to the target file or directory")
    content: str | FileModificationContent | None = Field(
        None,
        description=(
            "Content for the file operation:\n"
            "- For 'create_file': String content of the new file\n"
            "- For 'modify_file': FileModificationContent object specifying modifications\n"
            "- For other operations: Should be None"
        ),
    )

    def validate_content_type(self) -> bool:
        """Validates that the content field matches the expected type based on operation type"""
        if self.type == "create_file" and not isinstance(self.content, str):
            return False
        if self.type == "modify_file" and not isinstance(self.content, FileModificationContent):
            return False
        if self.type in ["delete_file", "delete_directory", "create_directory"] and self.content is not None:
            return False
        return True
