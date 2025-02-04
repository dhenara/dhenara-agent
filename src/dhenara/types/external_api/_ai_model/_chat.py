# Copyright 2024-2025 Dhenara Inc. All rights reserved.

from typing import Any, Union

from dhenara.types.base import BaseModel
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


class ChatResponseMetaDataOpenAi(BaseModel):
    """OpenAI specific metadata for chat responses"""

    id: str
    object: str
    created: int
    system_fingerprint: str


class ChatResponseMetaDataGoogleAi(BaseModel):
    """Google AI specific metadata for chat responses"""

    prompt_feedback: dict | None = None


class ChatResponseMetaDataAnthropic(BaseModel):
    """Anthropic specific metadata for chat responses"""

    id: str
    type: str


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
