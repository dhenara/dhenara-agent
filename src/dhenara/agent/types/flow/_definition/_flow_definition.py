
from pydantic import Field

from dhenara.agent.types.flow import (
    BaseFlow,
    ExecutionStrategyEnum,
)
from dhenara.ai.types.shared.base import BaseModel


class FlowDefinition(BaseModel):
    execution_strategy: ExecutionStrategyEnum = Field(
        ...,
        description="Execution strategy for top-level nodes",
        examples=["sequential"],
    )

    flows: list[BaseFlow] = Field(
        ...,
        description="List of nodes in execution order",
        min_items=1,
    )
