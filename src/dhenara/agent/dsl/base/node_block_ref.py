from typing import Any, Generic, TypeVar

from pydantic import Field, field_validator

from dhenara.agent.dsl.base import ExecutableElement, ExecutableNodeDefinition, ExecutionContext, NodeID
from dhenara.agent.types.base import BaseModel

ElementT = TypeVar("ElementT", bound=ExecutableElement)
ContextT = TypeVar("ContextT", bound=ExecutionContext)

NodeDefT = TypeVar("NodeDefT", bound=ExecutableNodeDefinition)


# A generic node that could later be specialized
class ExecutableNode(BaseModel, Generic[ElementT, NodeDefT, ContextT]):
    """A single execution node in the DSL."""

    id: NodeID = Field(
        ...,
        description="Unique human readable identifier for the node",
        min_length=1,
        max_length=150,
        pattern="^[a-zA-Z0-9_]+$",
    )
    info: str | None = Field(
        default=None,
        description="General purpose string for user display",
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


class ExecutableBlock(Generic[ElementT, ContextT]):
    elements: list[ElementT] = Field(
        ...,
        description="The elements (nodes/sub-blocks) in this block.",
    )

    def __init__(self, elements: list[ElementT]):
        self.elements = elements

    async def execute(self, execution_context: ContextT) -> list[Any]:
        """Execute all elements in this block sequentially."""
        results = []
        for element in self.elements:
            result = await element.execute(execution_context)
            results.append(result)
        return results


class ExecutableReference(Generic[ElementT, ContextT]):
    """A reference to a value in the execution_context."""

    def __init__(self, path: str):
        self.path = path

    async def execute(self, execution_context: ContextT) -> Any:
        """Get the referenced value from the execution_context."""
        return execution_context.get_value(self.path)
