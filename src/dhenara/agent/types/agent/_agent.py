from typing import NewType

from dhenara.agent.types.flow import FlowDefinition
from dhenara.ai.types.shared.base import BaseModel
from pydantic import Field

AgentIdentifier = NewType("AgentIdentifier", str)


class Agent(BaseModel):
    identifier: AgentIdentifier = Field(
        ...,
        description="Unique human readable identifier for the agent ",
        min_length=1,
        max_length=150,
        pattern="^[a-zA-Z0-9_-]+$",
    )
    description: str | None = Field(
        ...,
        description="Optional description",
    )
    flow_definition: FlowDefinition = Field(
        ...,
        description="Flow Definition",
    )
    enabled: bool = Field(
        default=True,
        description="Active or not",
    )
    multi_phase: bool = Field(
        ...,
        description="Single Phase or Multi Phase",
    )
    independent: bool = Field(
        ...,
        description="Whether depended on other agent execution",
    )
    order: int = Field(
        default=0,
        description="Order",
        ge=0,
    )
