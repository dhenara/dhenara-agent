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


class ExecutableBlock(Generic[ElementT, ContextT]):
    elements: list[ElementT] = Field(
        ...,
        description="The elements (nodes/sub-blocks) in this block.",
    )

    def __init__(self, elements: list[ElementT]):
        self.elements = elements

    # Without reruns
    # async def execute(self, execution_context: ContextT) -> list[Any]:
    #    """Execute all elements in this block sequentially."""
    #    results = []
    #    for element in self.elements:
    #        result = await element.execute(execution_context)
    #        results.append(result)
    #    return results

    async def execute(self, execution_context: ContextT) -> list[Any]:
        """Execute all elements in this block sequentially.

        If start_node_id is specified, skip elements until the starting node is found.
        """
        results = []
        start_node_id = getattr(execution_context, "start_node_id", None)
        start_execution = start_node_id is None  # Start immediately if no start_node_id

        for element in self.elements:
            # Check if this is the node we should start from
            element_id = getattr(element, "id", None)

            if not start_execution and element_id == start_node_id:
                # Found our starting point, begin execution
                start_execution = True
                execution_context.logger.info(f"Starting execution from node {start_node_id}")

            if start_execution:
                result = await element.execute(execution_context)
                results.append(result)
            else:
                result = await element.load_from_previous_run(execution_context)
                results.append(result)

        return results


class ExecutableReference(Generic[ElementT, ContextT]):
    """A reference to a value in the execution_context."""

    def __init__(self, path: str):
        self.path = path

    async def execute(self, execution_context: ContextT) -> Any:
        """Get the referenced value from the execution_context."""
        return execution_context.get_value(self.path)
