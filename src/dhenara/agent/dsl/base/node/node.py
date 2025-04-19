from typing import Any, Generic, TypeVar

from pydantic import Field, field_validator

from dhenara.agent.dsl.base import ContextT, Executable, NodeDefT, NodeID
from dhenara.agent.types.base import BaseModel


# A generic node that could later be specialized
class ExecutableNode(Executable, BaseModel, Generic[NodeDefT, ContextT]):
    """
    A single execution node in the DSL.
    Wraps a node definition with a unique identifier so that it becomes executable.
    """

    id: NodeID = Field(
        ...,
        description="Unique human readable identifier for the node",
        min_length=1,
        max_length=150,
        pattern="^[a-zA-Z0-9_]+$",
    )

    definition: NodeDefT = Field(...)

    @field_validator("id")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate node identifier format.
        Raises ValueError if identifier is empty or contains only whitespace
        """
        if not v.strip():
            raise ValueError("FlowNode identifier cannot be empty or whitespace")
        return v

    async def execute(self, execution_context: ContextT) -> Any:
        result = await self.definition.execute(
            node_id=self.id,
            execution_context=execution_context,
        )

        return result

    async def load_from_previous_run(self, execution_context: ContextT) -> Any:
        execution_context.logger.info(f"Loading previous run data for node {self.id} ")

        result = await self.definition.load_from_previous_run(
            node_id=self.id,
            execution_context=execution_context,
        )
        return result


NodeT = TypeVar("NodeT", bound=ExecutableNode)
