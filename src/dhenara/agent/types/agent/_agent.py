from typing import NewType

from dhenara.ai.types.shared.base import BaseModel
from pydantic import Field

AgentIdentifier = NewType("AgentIdentifier", str)

class Agent(BaseModel):
    order: int = Field(
        default=0,
        description="Order",
        ge=0,
        examples=[1],
    )
    identifier: AgentIdentifier = Field(
        ...,
        description="Unique human readable identifier for the node",
        min_length=1,
        max_length=150,
        pattern="^[a-zA-Z0-9_-]+$",
    )
    multi_phase: bool= Field(
        ...,
        description="Single Phase or Multi Phase",
    )
    independent: bool= Field(
        ...,
        description="Whether depended on other agent execution",
    )



