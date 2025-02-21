from dhenara.types.base import BaseModel
from pydantic import Field


class BaseResponseContentItem(BaseModel):
    """Base content item for AI model responses

    Contains common metadata fields used across different types of AI responses

    Attributes:
        metadata: System-generated metadata from API response
        storage_metadata: Storage-related metadata (e.g., cloud storage information)
        custom_metadata: User-defined additional metadata
    """

    metadata: dict = Field(
        default_factory=dict,
        description="System-generated metadata from API response processing",
    )
    storage_metadata: dict = Field(
        default_factory=dict,
        description="User-defined storage-related metadata such as cloud storage details, paths, or references. Will be empty on output from `dhenara-ai` package.",
    )
    custom_metadata: dict = Field(
        default_factory=dict,
        description="User-defined additional metadata for custom processing or tracking. Will be empty on output from `dhenara-ai` package",
    )


class ChatResponseContentItem(BaseResponseContentItem):
    """Content item specific to chat responses

    Contains the role, text content, and optional function calls for chat interactions

    Attributes:
        role: The role of the message sender (system, user, assistant, or function)
        text: The actual text content of the message
        function_call: Optional function call details if the message involves function calling
    """

    role: str = Field(
        ...,
        description="Role of the message sender in the chat context",
    )
    text: str | None = Field(
        None,
        description="Text content of the message",
        min_length=1,
        max_length=100000,
    )
    function_call: dict | None = Field(
        None,
        description="Function call details including name and arguments",
    )


class ImageResponseContentItem(BaseResponseContentItem):
    """Content item specific to image generation responses

    Contains the generated image data in various formats (bytes, base64, or URL)

    Attributes:
        content_bytes: Raw image bytes
        content_b64_json: Base64 encoded image data
        content_url: URL to the generated image
        format: Image format (e.g., PNG, JPEG)
        size: Image dimensions
    """

    content_bytes: bytes | None = Field(
        None,
        description="Raw image content in bytes",
    )
    content_b64_json: str | None = Field(
        None,
        description="Base64 encoded image content",
        min_length=1,
    )
    content_url: str | None = Field(
        None,
        description="URL to access the generated image",
        pattern=r"^https?://.*$",
    )
    format: str = Field(
        "PNG",
        description="Image format (e.g., PNG, JPEG)",
    )
    size: tuple[int, int] | None = Field(
        None,
        description="Image dimensions (width, height)",
    )

    def validate_content(self) -> bool:
        """Validates that at least one content field is populated

        Returns:
            bool: True if at least one content field has data
        """
        return any(
            [
                self.content_bytes is not None,
                self.content_b64_json is not None,
                self.content_url is not None,
            ]
        )
