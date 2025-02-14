# Copyright 2024-2025 Dhenara Inc. All rights reserved.

from typing import Union

from dhenara.types.base import BaseModel
from dhenara.types.external_api._providers import AIModelProvider


class ImageResponseContentItem(BaseModel):
    """Content item in an image generation response

    Contains the generated image information including file references and status
    """

    tsg_file_id: str | None = None
    content_url_from_api: str | None = None
    revised_prompt: str | None = None
    rai_filtered_reason: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "tsg_file_id": "file_123abc",
                "content_url_from_api": "https://api.example.com/images/123.jpg",
                "revised_prompt": "A serene mountain landscape at sunset",
                "rai_filtered_reason": None,
            }
        }


class ImageResponseChoice(BaseModel):
    """A single image generation choice/result"""

    index: int
    content: ImageResponseContentItem

    class Config:
        json_schema_extra = {
            "example": {
                "index": 0,
                "content": {
                    "tsg_file_id": "file_123abc",
                    "content_url_from_api": "https://api.example.com/images/123.jpg",
                },
            }
        }


class ImageResponseUsage(BaseModel):
    """Usage information for image generation"""

    model: str
    cost_affecting_options: dict

    class Config:
        json_schema_extra = {
            "example": {
                "model": "dall-e-3",
                "cost_affecting_options": {
                    "size": "1024x1024",
                    "quality": "standard",
                },
            }
        }


class ImageResponseMetaDataOpenAi(BaseModel):
    """OpenAI specific metadata for image responses"""

    id: str
    object: str
    created: int
    system_fingerprint: str


class ImageResponseMetaDataGoogleAi(BaseModel):
    """Google AI specific metadata for image responses"""

    prompt_feedback: dict | None = None


class ImageResponseMetaDataAnthropic(BaseModel):
    """Anthropic specific metadata for image responses"""

    id: str
    type: str


class ImageResponse(BaseModel):
    """Complete response from an AI image generation model

    Contains the generated images, usage information, and provider-specific metadata
    """

    model: str
    provider: AIModelProvider
    usage: ImageResponseUsage
    cost_in_usd: str
    choices: list[ImageResponseChoice]
    metadata: Union[
        ImageResponseMetaDataOpenAi,
        ImageResponseMetaDataGoogleAi,
        ImageResponseMetaDataAnthropic,
        dict,
    ] = {}

    class Config:
        json_schema_extra = {
            "example": {
                "model": "dall-e-3",
                "provider": "openai",
                "usage": {
                    "model": "dall-e-3",
                    "cost_affecting_options": {
                        "size": "1024x1024",
                        "quality": "standard",
                    },
                },
                "cost_in_usd": "0.040",
                "choices": [
                    {
                        "index": 0,
                        "content": {
                            "tsg_file_id": "file_123abc",
                            "content_url_from_api": "https://api.example.com/images/123.jpg",
                        },
                    }
                ],
                "metadata": {
                    "id": "img-123abc",
                    "object": "image.generation",
                    "created": 1677649420,
                    "system_fingerprint": "fp-123",
                },
            }
        }
