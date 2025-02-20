# Copyright 2024-2025 Dhenara Inc. All rights reserved.

from typing import Any

from dhenara.types.api import SSEDataChunk, SSEEventType, SSEResponse
from dhenara.types.base import BaseModel
from dhenara.types.external_api._providers import AIModelAPIProviderEnum, AIModelProviderEnum


class AIModelCallResponseMetaData(BaseModel):
    streaming: bool = False
    duration_seconds: int | float | None = None
    provider_data: dict


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
    finish_reason: Any | None = None
    stop_sequence: Any | None = None
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


class ChatResponseMetaDataOpenAi(BaseModel):
    """OpenAI specific metadata for chat responses"""

    id: str
    object: str  # object type : chat.completion
    created: int | None = None  # Unix timestamp (in seconds) of creation
    system_fingerprint: str


class ChatResponseMetaDataGoogleAi(BaseModel):
    """Google AI specific metadata for chat responses"""

    prompt_feedback: dict | None = None


class ChatResponseMetaDataAnthropic(BaseModel):
    """Anthropic specific metadata for chat responses"""

    id: str
    type: str


# Streaming
class TokenStreamChunk(SSEDataChunk):
    """Specialized chunk for token streaming"""

    pass
    # token_count: int | None = Field(
    #    default=None,
    #    description="Number of tokens in this chunk",
    # )
    # model: str | None = Field(
    #    default=None,
    #    description="Model generating the tokens",
    # )


class StreamingChatResponse(SSEResponse[TokenStreamChunk]):
    """Specialized SSE response for chat streaming"""

    event: SSEEventType = SSEEventType.TOKEN_STREAM
    data: TokenStreamChunk


class ChatResponse(BaseModel):
    """Complete chat response from an AI model

    Contains the response content, usage statistics, and provider-specific metadata
    """

    model: str
    provider: AIModelProviderEnum
    api_provider: AIModelAPIProviderEnum | None = None
    usage: ChatResponseUsage
    cost_in_usd: str
    choices: list[ChatResponseChoice]
    metadata: AIModelCallResponseMetaData | dict = {}

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
