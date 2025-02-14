from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from dhenara.types.base import BaseModel
from dhenara.types.external_api import AIModelAPIProvider


class AIModelAPI(BaseModel):
    """
    Pydantic model representing API credentials for AI model providers.
    """

    provider: AIModelAPIProvider = Field(
        ...,
        description="The AI model provider",
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional notes about the credentials",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration settings for the provider",
    )
    enabled: bool = Field(
        True,  # noqa: FBT003
        description="Whether these credentials are enabled",
    )
    is_instance_wide: bool = Field(
        False,  # noqa: FBT003
        description="Whether these credentials are available instance-wide",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )
    api_key: Optional[str] = Field(
        None,
        description="API key for authentication",
    )
    dict_credentials: Optional[dict[str, Any]] = Field(
        None,
        description="Dictionary of additional credentials",
    )
    reference_number: str | None = Field(
        None,
        description="reference number. Should be unique if not None",
    )
