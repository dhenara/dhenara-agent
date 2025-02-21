# Copyright 2024-2025 Dhenara Inc. All rights reserved.


from dhenara.types.base import BaseModel
from dhenara.types.external_api._providers import AIModelProviderEnum
from pydantic import Field

from ._chat import AIModelCallResponseMetaData
from ._content_item import ImageResponseContentItem


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
    """Usage information for image generation. Note that, for images, no usage data is received, so this class holds params required for usage/cost calculation"""

    model: str = Field(
        default_factory=dict,
        description="Model Name",
    )
    options: dict = Field(
        default_factory=dict,
        description="Options send to API",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "model": "dall-e-3",
                "options": {
                    "size": "1024x1024",
                    "quality": "standard",
                },
            }
        }


class ImageResponse(BaseModel):
    """Complete response from an AI image generation model

    Contains the generated images, usage information, and provider-specific metadata
    """

    model: str
    provider: AIModelProviderEnum
    usage: ImageResponseUsage
    cost_in_usd: str
    choices: list[ImageResponseChoice]
    metadata: AIModelCallResponseMetaData | dict = {}

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
