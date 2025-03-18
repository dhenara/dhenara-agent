from typing import ClassVar

from pydantic import Field

from dhenara.agent.types.flow import (
    FlowIdentifier,
    FlowTypeEnum,
)
from dhenara.ai.types.shared.base import BaseModel


class BaseFlow(BaseModel):
    """Base class for all flow definitions."""

    flow_type: ClassVar[FlowTypeEnum | None] = None

    order: int = Field(
        ...,
        description="Execution sequence number",
        ge=0,
        examples=[1],
    )

    identifier: FlowIdentifier = Field(
        ...,
        description="Unique human readable identifier for the flow",
        min_length=1,
        max_length=150,
        pattern="^[a-zA-Z0-9_-]+$",
        examples=["initial_model_call", "context_retrieval", "final_summary"],
    )
    info: str | None = Field(
        default=None,
        description=("General purpose string. Can be user to show a message to the user while executing this node"),
    )

    system_instructions: list[str] | None = Field(
        default=None,
        description="Flow-wide system instructions",
    )
