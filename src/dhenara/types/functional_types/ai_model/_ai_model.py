from typing import Any

from pydantic import Field

from dhenara.types.base import BaseModel
from dhenara.types.external_api._providers import AIModelFunctionalTypeEnum, AIModelProviderEnum


class AIModel(BaseModel):
    """
    Pydantic model representing an AI model configuration.
    """

    provider: AIModelProviderEnum = Field(
        ...,
        description="The AI model provider",
    )
    functional_type: AIModelFunctionalTypeEnum = Field(
        ...,
        description="Type of AI model functionality",
    )
    model_name: str = Field(
        ...,
        max_length=300,
        description="model name used in API calls",
    )
    display_name: str = Field(
        ...,
        max_length=300,
        description="Display name for the model",
    )
    notes: str | None = Field(
        None,
        max_length=500,
        description="Optional notes about the model",
    )
    display_order: int = Field(
        0,
        description="Order for display purposes",
    )
    enabled: bool = Field(
        True,  # noqa: FBT003
        description="Whether the model is enabled",
    )
    is_beta: bool = Field(
        False,  # noqa: FBT003
        description="Whether the model is in beta",
    )

    max_context_window_tokens: int | None = Field(
        None,
        description="Maximum context window size in tokens",
    )
    max_input_tokens: int | None = Field(
        None,
        description="Maximum input tokens allowed",
    )
    max_output_tokens: int | None = Field(
        None,
        description="Maximum output tokens allowed",
    )
    settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional settings for the model",
    )
    is_instance_wide: bool = Field(
        False,  # noqa: FBT003
        description="Whether the model is available instance-wide",
    )
    reference_number: str | None = Field(
        None,
        description="reference number. Should be unique if not None",
    )
