import json
from typing import Any

from dhenara_ai.types.shared.base import BaseModel

# from urllib.request import urlopen
from pydantic import AnyUrl, Field

from dhenara.types.flow import ContentType, FlowNodeUserInputActionEnum


# TODO: Implement Option to pass User Input to each node
class UserInput(BaseModel):
    """Represents user input data for AI model processing.

    This model handles various forms of input content including text, URLs, and JSON data
    that can be processed by AI models.

    Attributes:
        content: Single text content for processing.
        contents: Multiple text contents for batch processing.
        content_urls: List of URLs pointing to content files.
        content_json: Structured JSON data for processing.
        content_jsonl: List of JSON objects in JSONL format.
        options: Configuration options for AI model behavior.

    Example:
        ```python
        user_input = UserInput(
            content="What is the capital of France?",
            options={"temperature": 0.7, "max_tokens": 100},
        )
        ```
    """

    action: FlowNodeUserInputActionEnum | None = Field(
        default=None,
        description="Type of API action to perform, if any",
    )

    meta: dict = Field(
        default_factory=dict,
        description="Inputs metadata",
        example={"sub_action": "my_custom_acion"},
    )

    content: str | None = Field(
        default=None,
        description="Primary text content to be processed",
        example="What is the capital of France?",
        # max_length=8192,
    )

    contents: list[str] | None = Field(
        default=None,
        description="Multiple text contents for batch processing",
        example=["Text 1", "Text 2"],
        max_length=100,  # Maximum number of items in list
    )

    content_urls: list[AnyUrl] | None = Field(
        default=None,
        description="URLs pointing to content files for processing",
        example=["https://example.com/file1.txt", "https://example.com/file2.txt"],
        max_length=50,  # Maximum number of URLs
    )

    content_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured JSON data for processing",
        example={"key": "value"},
    )

    content_jsonl: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of JSON objects in JSONL format",
        example=[{"id": 1, "text": "example"}, {"id": 2, "text": "example2"}],
        max_length=1000,  # Maximum number of JSONL entries
    )

    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration options for the AI model behavior",
        example={
            "temperature": 0.7,
            "max_tokens": 100,
            "top_p": 1.0,
        },
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "examples": [
                {
                    "content": "What is the capital of France?",
                    "options": {
                        "temperature": 0.7,
                        "max_tokens": 100,
                    },
                },
                {
                    "contents": ["Text 1", "Text 2"],
                    "content_json": {"key": "value"},
                    "content_jsonl": [{"id": 1, "text": "example"}],
                },
            ],
        }

    @property
    def has_content(self) -> bool:
        """Check if the input contains any content.

        Returns:
            bool: True if any content field is populated, False otherwise.
        """
        return any(
            [
                self.content is not None,
                self.contents is not None,
                self.content_urls is not None,
                bool(self.content_json),
                bool(self.content_jsonl),
            ]
        )

    # def validate_content_length(self, content: str) -> str:
    #    if len(content) > 8192:
    #        raise ValueError("Content exceeds maximum length of 8192 characters")
    #    return content

    async def get_content(
        self,
        return_type: ContentType = ContentType.TEXT,
        separator: str = "\n",
    ) -> str | list[str] | dict | list[dict]:
        """Retrieve content from any of the input sources.

        This method consolidates content from various input fields and returns it in the
        requested format. It handles text content, URLs, JSON, and JSONL data.

        Args:
            return_type: Desired return type format (text, list, dict, or jsonl)
            separator: String separator for joining text content when return_type is TEXT

        Returns:
            Content in the requested format:
            - TEXT: Single string with all content joined
            - LIST: List of strings
            - DICT: Dictionary from content_json
            - JSONL: List of dictionaries from content_jsonl

        Examples:
            ```python
            # Get as single text
            content = await user_input.get_content(return_type=ContentType.TEXT)

            # Get as list
            content_list = await user_input.get_content(return_type=ContentType.LIST)

            # Get as dict
            content_dict = await user_input.get_content(return_type=ContentType.DICT)
            ```

        Raises:
            ValueError: If no content is available or if requested format is incompatible
        """
        if not self.has_content:
            raise ValueError("No content available in any field")

        # Collect all text content
        text_contents: list[str] = []

        # Add single content if present
        if self.content:
            text_contents.append(self.content)

        # Add multiple contents if present
        if self.contents:
            text_contents.extend(self.contents)

        # Add URL contents if present
        if self.content_urls:
            pass
            # for url in self.content_urls:
            #    try:
            #        async with urlopen(str(url)) as response:
            #            text_contents.append(await response.read().decode())
            #    except Exception as e:
            #        raise ValueError(f"Failed to fetch content from URL {url}: {e}")

        # Return based on requested type
        if return_type == ContentType.TEXT:
            # Include JSON content if present
            if self.content_json:
                text_contents.append(json.dumps(self.content_json, ensure_ascii=False))
            if self.content_jsonl:
                text_contents.extend(json.dumps(item, ensure_ascii=False) for item in self.content_jsonl)
            return separator.join(text_contents)

        elif return_type == ContentType.LIST:
            return text_contents

        elif return_type == ContentType.DICT:
            if not self.content_json:
                raise ValueError("No JSON content available")
            return self.content_json

        elif return_type == ContentType.JSONL:
            if not self.content_jsonl:
                raise ValueError("No JSONL content available")
            return self.content_jsonl

    def get_options(self, default: dict | None = None) -> dict[str, Any]:
        """Get options with optional defaults.

        Args:
            default: Default options to use if none are set

        Returns:
            Dictionary of options, merged with defaults if provided
        """
        if default is None:
            default = {}

        if self.options is None:
            return default

        return {**default, **self.options}

    @property
    def primary_content(self) -> str | None:
        """Get the primary content if available.

        Returns:
            The primary content string or None if not available
        """
        if self.content:
            return self.content
        if self.contents and self.contents[0]:
            return self.contents[0]
        if self.content_json:
            return json.dumps(self.content_json, ensure_ascii=False)
        if self.content_jsonl and self.content_jsonl[0]:
            return json.dumps(self.content_jsonl[0], ensure_ascii=False)
        return None
