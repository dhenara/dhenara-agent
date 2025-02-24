# Copyright 2024-2025 Dhenara Inc. All rights reserved.
import logging
from typing import Annotated, Any, Literal, Union

from pydantic import Field, field_validator

from dhenara.types.base import BaseModel
from dhenara.types.external_api import (
    AnthropicMessageRoleEnum,
    GoogleAiMessageRoleEnum,
    OpenAiMessageRoleEnum,
)

logger = logging.getLogger(__name__)


# OpenAI Specific Models


class OpenAITextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class OpenAIImageUrlContent(BaseModel):
    url: str


class OpenAIImageContent(BaseModel):
    type: Literal["image_url"] = "image_url"
    image_url: OpenAIImageUrlContent


# Discriminated union for content parts
ContentPart = Annotated[Union[OpenAITextContent, OpenAIImageContent], Field(discriminator="type")]


class OpenAIPromptMessage(BaseModel):
    role: OpenAiMessageRoleEnum
    content: Union[str, list[ContentPart]]
    function_call: dict[str, Any] | None = None

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v):
        # Handle string case
        if isinstance(v, str):
            return v

        # Handle list case with automatic discrimination
        if isinstance(v, list):
            return [{"type": item.get("type"), **item} for item in v]

        raise ValueError("Content must be string or list of content parts")

    # fmt: off
    def model_dump(self, **kwargs):
        # Clean None values and empty lists
        data = super().model_dump(**kwargs)

        if isinstance(data["content"], list):
            data["content"] = [
                part for part in data["content"]
                if (part["type"] == "text" and part["text"]) or
                   (part["type"] == "image_url" and part["image_url"]["url"])
                ]

        if not data["content"] and isinstance(data["content"], list):
            data["content"] = ""  # Fallback to empty string

        return data


# Anthropic Specific Models


class AnthropicMessageTextContent(BaseModel):
    type: Literal["text"]
    text: str


class AnthropicMessageImageContent(BaseModel):
    type: Literal["image"]
    source: dict  # Or use a more specific type for image source


class AnthropicPromptMessage(BaseModel):
    role: AnthropicMessageRoleEnum
    content: Union[str, list[Union[AnthropicMessageTextContent, AnthropicMessageImageContent]]]

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if isinstance(v, str):
            return v

        for item in v:
            if isinstance(item, dict):
                if item["type"] == "text":
                    if "source" in item:
                        item.pop("source")  # Remove source field for text content
                elif item["type"] == "image" and "source" not in item:
                    raise ValueError("source is required for image type")
        return v


# Google AI Specific Models


class GoogleAITextPart(BaseModel):
    text: str


class GoogleAIInlineDataPart(BaseModel):
    inline_data: dict[str, str] = Field(..., alias="inline_data")


class GoogleAIPromptMessage(BaseModel):
    """A complete Google AI prompt message"""

    role: GoogleAiMessageRoleEnum
    parts: list[Union[GoogleAITextPart, GoogleAIInlineDataPart]]

    @field_validator("parts", mode="before")
    @classmethod
    def validate_parts(cls, v):
        validated_parts = []

        if isinstance(v, str):
            # Convert single string to text part
            return [GoogleAITextPart(text=v)]

        for part in v:
            if isinstance(part, str):
                validated_parts.append(GoogleAITextPart(text=part))
            elif isinstance(part, dict):
                if "text" in part:
                    validated_parts.append(GoogleAITextPart(**part))
                elif "inline_data" in part:
                    validated_parts.append(GoogleAIInlineDataPart(**part))
            elif isinstance(part, (GoogleAITextPart, GoogleAIInlineDataPart)):
                validated_parts.append(part)

        return validated_parts

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        data["parts"] = [part.model_dump() for part in self.parts]
        return data


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
