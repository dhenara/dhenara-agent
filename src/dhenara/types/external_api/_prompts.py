# Copyright 2024-2025 Dhenara Inc. All rights reserved.
import logging
from typing import Any, Literal, Union

from pydantic import BaseModel, field_validator

from dhenara.types.external_api import (
    AnthropicMessageRoleEnum,
    GoogleAiMessageRoleEnum,
    OpenAiMessageRoleEnum,
)

logger = logging.getLogger(__name__)


# Base Content Models
class BasePromptFileContent(BaseModel):
    """Base model for file content validation"""

    type: str
    text: str | None = None

    @field_validator("text")
    def validate_text_content(cls, v, values):
        if values.get("type") == "text" and not v:
            raise ValueError("text is required for text type content")
        return v


# OpenAI Specific Models
class OpenAIImageContent(BaseModel):
    url: str


class OpenAIPromptFileContent(BasePromptFileContent):
    type: Literal["text", "image_url"]
    image_url: OpenAIImageContent | None = None

    @field_validator("image_url")
    @classmethod
    def validate_image_content(cls, v, values):
        if values.get("type") == "image_url" and not v:
            raise ValueError("image_url is required for image_url type")
        return v


class OpenAIPromptMessage(BaseModel):
    role: OpenAiMessageRoleEnum
    content: Union[str, list[OpenAIPromptFileContent]]
    function_call: dict[str, Any] | None = None


# Anthropic Specific Models
class AnthropicImageContent(BaseModel):
    type: Literal["base64"]
    media_type: str
    data: str


class AnthropicPromptFileContent(BasePromptFileContent):
    type: Literal["text", "image"]
    source: AnthropicImageContent | None = None

    @field_validator("source")
    @classmethod
    def validate_image_source(cls, v, values):
        if values.get("type") == "image" and not v:
            raise ValueError("source is required for image type")
        return v


class AnthropicPromptMessage(BaseModel):
    role: AnthropicMessageRoleEnum
    content: Union[str, list[AnthropicPromptFileContent]]


# Google AI Specific Models
class GoogleAIPromptFileContent(BasePromptFileContent):
    type: Literal["text", "inline_data"]
    inline_data: dict[str, str] | None = None


class GoogleAIPromptMessage(BaseModel):
    role: GoogleAiMessageRoleEnum
    parts: list[GoogleAIPromptFileContent]


# # Configuration Models
# class PromptConfig(BaseModel):
#     model_provider: AIModelProviderEnum
#     max_tokens_query: int | None = Field(default=None, gt=0)
#     max_tokens_files: int | None = Field(default=None, gt=0)
#     max_tokens_response: int | None = Field(default=None, gt=0)
#     response_before_query: bool = False
#
#
# class ConversationNodeContent(BaseModel):
#     user_query: str | None = None
#     attached_files: list[GenericFile] | None = None
#     previous_response: Union[ChatResponse, ImageResponse] | None = None


FormattedPrompt = Union[OpenAIPromptMessage, GoogleAIPromptMessage, AnthropicPromptMessage]
SystemInstructions = list[str]
