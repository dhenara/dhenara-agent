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


# OpenAI Specific Models
class OpenAITextContent(BaseModel):
    """Model for text content"""

    type: Literal["text"]
    text: str


class OpenAIImageUrlContent(BaseModel):
    """Model for image URL content"""

    url: str


class OpenAIImagePart(BaseModel):
    """Model for image part"""

    type: Literal["image_url"]
    image_url: OpenAIImageUrlContent


class OpenAIPromptPart(BaseModel):
    """Combined model for all content types"""

    type: Literal["text", "image_url"]
    text: str | None = None
    image_url: OpenAIImageUrlContent | None = None

    @field_validator("*", mode="before")
    @classmethod
    def validate_content(cls, v, info):
        field_name = info.field_name
        if field_name == "type":
            return v
        if v is None:
            return None
        return v

    @field_validator("text", "image_url")
    @classmethod
    def validate_required_fields(cls, v, info):
        field_name = info.field_name
        content_type = info.data.get("type")

        if content_type == "text" and field_name == "text" and not v:
            raise ValueError("text is required for text type content")
        if content_type == "image_url" and field_name == "image_url" and not v:
            raise ValueError("image_url is required for image_url type")
        return v

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        return {k: v for k, v in data.items() if v is not None}


class OpenAIPromptMessage(BaseModel):
    """Complete OpenAI message model"""

    role: OpenAiMessageRoleEnum
    content: Union[str, list[OpenAIPromptPart]]
    function_call: dict[str, Any] | None = None

    # fmt: off
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if isinstance(v, str):
            return v
        elif isinstance(v, list):
            validated_parts = []
            for part in v:
                if isinstance(part, dict):
                    if part.get('type') == 'text':
                        validated_parts.append(OpenAIPromptPart(
                            type='text',
                            text=part.get('text')
                        ))
                    elif part.get('type') == 'image_url':
                        validated_parts.append(OpenAIPromptPart(
                            type='image_url',
                            image_url=part.get('image_url')
                        ))
                elif isinstance(part, OpenAIPromptPart):
                    validated_parts.append(part)
            return validated_parts
        raise ValueError("content must be either a string or a list of parts")

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if isinstance(data['content'], list):
            data['content'] = [
                part for part in data['content']
                if (part.get('type') == 'text' and part.get('text')) or
                   (part.get('type') == 'image_url' and part.get('image_url'))
            ]
        return data
    # fmt: on


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
    inline_data: dict[str, str]


class GoogleAIPromptPart(BaseModel):
    """A single part of a Google AI prompt"""

    text: str | None = None
    inline_data: dict[str, str] | None = None

    @field_validator("*", mode="before")
    @classmethod
    def validate_content(cls, v, info):
        field_name = info.field_name
        if field_name == "text" and v is not None:
            return v
        if field_name == "inline_data" and v is not None:
            return v
        return None

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        return {k: v for k, v in data.items() if v is not None}


class GoogleAIPromptMessage(BaseModel):
    """A complete Google AI prompt message"""

    role: GoogleAiMessageRoleEnum
    parts: Union[str, list[GoogleAIPromptPart]]

    @field_validator("parts")
    @classmethod
    def validate_parts(cls, v):
        if isinstance(v, str):
            return [GoogleAIPromptPart(text=v)]
        elif isinstance(v, list):
            validated_parts = []
            for part in v:
                if isinstance(part, str):
                    validated_parts.append(GoogleAIPromptPart(text=part))
                elif isinstance(part, dict):
                    if "text" in part:
                        validated_parts.append(GoogleAIPromptPart(text=part["text"]))
                    elif "inline_data" in part:
                        validated_parts.append(GoogleAIPromptPart(inline_data=part["inline_data"]))
                elif isinstance(part, GoogleAIPromptPart):
                    validated_parts.append(part)
            return validated_parts
        raise ValueError("parts must be either a string or a list of parts")

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if isinstance(data["parts"], list):
            data["parts"] = [part for part in data["parts"] if part.get("text") is not None or part.get("inline_data") is not None]
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
