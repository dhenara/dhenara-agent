from pydantic import Field

from dhenara.agent.dsl.base import ExecutableNodeID
from dhenara.agent.dsl.flow import Flow
from dhenara.agent.types.base import BaseModel


class AgentNode(BaseModel):  # TODO_FUTURE:  AgentNode & AgentNodeDefinition
    id: ExecutableNodeID = Field(
        ...,
        description="Unique human readable identifier for the agent",
        min_length=1,
        max_length=150,
        pattern="^[a-zA-Z0-9_-]+$",
    )
    info: str | None = Field(
        default=None,
        description=("General purpose string. Can be user to show a message to the user while executing this agent"),
    )
    description: str | None = Field(
        ...,
        description="Optional description",
    )
    flow: Flow = Field(
        ...,
        description="Flow",
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
