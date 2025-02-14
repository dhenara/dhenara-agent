from decimal import Decimal
from typing import Any

from pydantic import Field

from dhenara.types.base import BaseModel
from dhenara.types.functional_types.ai_model import AIModel, AIModelAPI


class AIModelEndpoint(BaseModel):
    """
    Pydantic model representing an AI model endpoint configuration.
    """

    api: AIModelAPI = Field(
        ...,
        description="Reference to API credentials",
    )
    ai_model: AIModel = Field(
        ...,
        description="Reference to AI model",
    )
    notes: str | None = Field(
        None,
        max_length=500,
        description="Optional notes about the endpoint",
    )
    enabled: bool = Field(
        True,  # noqa: FBT003
        description="Whether the endpoint is enabled",
    )
    is_instance_wide: bool = Field(
        False,  # noqa: FBT003
        description="Whether the endpoint is available instance-wide",
    )
    input_token_cost_per_million: Decimal | None = Field(
        None,
        description="Cost per million input tokens",
    )
    output_token_cost_per_million: Decimal | None = Field(
        None,
        description="Cost per million output tokens",
    )
    flat_cost_image_cost: Decimal | None = Field(
        None,
        description="Flat cost for image generation",
    )
    image_options_cost_data: list[Any] = Field(
        default_factory=list,
        description="Cost data for image generation options",
    )
    display_order: int = Field(
        0,
        description="Order for display purposes",
    )
    reference_number: str | None = Field(
        None,
        description="reference number. Should be unique if not None",
    )
