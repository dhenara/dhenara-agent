# Copyright 2024-2025 Dhenara Inc. All rights reserved.

import json
from typing import Any, Union

from dhenara.types.base import BaseEnum, BaseModel
from dhenara.types.external_api._providers import AiModelProvider


class ChatResponseContentItem(BaseModel):
    """Content item in a chat response

    Contains the role and text of a message, along with optional function calls and metadata
    """

    role: str
    text: str
    function_call: Any | None = None
    metadata: dict | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "role": "assistant",
                "text": "Hello! How can I help you today?",
                "function_call": None,
                "metadata": {"confidence": 0.95},
            }
        }


class ChatResponseChoice(BaseModel):
    """A single choice/completion in the chat response"""

    index: int
    content: ChatResponseContentItem

    class Config:
        json_schema_extra = {
            "example": {
                "index": 0,
                "content": {
                    "role": "assistant",
                    "text": "Hello! How can I help you today?",
                },
            }
        }


class ChatResponseUsage(BaseModel):
    """Token usage statistics for the chat completion"""

    total_tokens: int
    prompt_tokens: int
    completion_tokens: int

    class Config:
        json_schema_extra = {
            "example": {
                "total_tokens": 100,
                "prompt_tokens": 50,
                "completion_tokens": 50,
            }
        }


class ChatResponseMetaDataBase(BaseModel):
    streaming: bool = False
    duration_seconds: int | float | None = None
    token_count: int | None = None


class ChatResponseMetaDataOpenAi(ChatResponseMetaDataBase):
    """OpenAI specific metadata for chat responses"""

    id: str
    object: str  # object type : chat.completion
    created: int | None = None  # Unix timestamp (in seconds) of creation
    system_fingerprint: str
    finish_reason: str | None = None


class ChatResponseMetaDataGoogleAi(ChatResponseMetaDataBase):
    """Google AI specific metadata for chat responses"""

    prompt_feedback: dict | None = None


class ChatResponseMetaDataAnthropic(ChatResponseMetaDataBase):
    """Anthropic specific metadata for chat responses"""

    id: str
    type: str


class StreamEventType(BaseEnum):
    """Types of streaming events (SSE Events)"""

    TOKEN = "token"  # New token/content in streaming mode chunk
    ERROR = "error"  # Error occurred
    # META = "meta"  # Metadata update


class StreamingChatResponse(BaseModel):
    """Model for streaming response chunks
    https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#event_stream_format
    """

    event: StreamEventType = StreamEventType.TOKEN
    id: str | None = None  # Optional event ID for reconnection
    retry: str | None = None
    # Data-fields
    index: int = 0
    content: str
    done: bool = False
    metadata: dict | None = None

    def to_sse_format(self) -> str:
        """Convert to SSE format string"""
        lines = []

        # Add event type if present
        if self.event:
            lines.append(f"event: {self.event}")

        # Add ID if present
        if self.id:
            lines.append(f"id: {self.id}")

        # Add ID if present
        if self.retry:
            lines.append(f"retry: {self.retry}")

        # Prepare data payload
        data = {
            "index": self.index,
            "content": self.content,
            "done": self.done,
            "metadata": self.metadata,
            # Passing some SSE fields as well
            "event": self.event,
        }
        if self.metadata:
            data["metadata"] = self.metadata

        # Add data (can be multiple lines)
        lines.append(f"data: {json.dumps(data)}")

        # End with double newline
        return "\n".join(lines) + "\n\n"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "event": self.event,
            "id": self.id,
            "index": self.index,
            "content": self.content,
            "done": self.done,
            "metadata": self.metadata,
        }


class ChatResponse(BaseModel):
    """Complete chat response from an AI model

    Contains the response content, usage statistics, and provider-specific metadata
    """

    model: str
    provider: AiModelProvider
    usage: ChatResponseUsage
    cost_in_usd: str
    choices: list[ChatResponseChoice]
    metadata: Union[
        ChatResponseMetaDataOpenAi,
        ChatResponseMetaDataGoogleAi,
        ChatResponseMetaDataAnthropic,
        dict,
    ] = {}

    def get_visible_fields(self) -> dict:
        return self.model_dump(exclude=["choices"])

    class Config:
        json_schema_extra = {
            "example": {
                "model": "gpt-4",
                "provider": "openai",
                "usage": {
                    "total_tokens": 100,
                    "prompt_tokens": 50,
                    "completion_tokens": 50,
                },
                "cost_in_usd": "0.002",
                "choices": [
                    {
                        "index": 0,
                        "content": {
                            "role": "assistant",
                            "text": "Hello! How can I help you today?",
                        },
                    }
                ],
                "metadata": {
                    "id": "chatcmpl-123",
                    "object": "chat.completion",
                    "created": 1677649420,
                    "system_fingerprint": "fp-123",
                },
            }
        }
