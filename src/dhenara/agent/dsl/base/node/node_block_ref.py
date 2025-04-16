from typing import Any, ClassVar, Generic, TypeVar

from pydantic import Field, field_validator

from dhenara.agent.dsl.base import ContextT, Executable, ExecutableT, NodeDefT, NodeID
from dhenara.agent.types.base import BaseModel


# A generic node that could later be specialized
class ExecutableNode(Executable, BaseModel, Generic[ExecutableT, NodeDefT, ContextT]):
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


NodeT = TypeVar("NodeT", bound=ExecutableNode)


# INFO: Not a Pydantic Class as the blocik is instanctiated  insided the component executor, which will casue error like
#  `not fully defined; you should define all referenced types, then call `Flow.model_rebuild()`.
class ExecutableBlock(Executable, Generic[ExecutableT, NodeT, ContextT]):
    id: NodeID
    elements: list[NodeT | "ExecutableBlock"]
    node_class: ClassVar[type[NodeT]]

    # INFO: Speial override for pythdatic , as the bloclk is instanctiated  insided the component executor
    def __init__(
        self,
        id,  # noqa: A002
        elements: list[ExecutableT],
    ):
        if not isinstance(elements, list):
            raise ValueError("elements must be a list")
        if not all(isinstance(e, (self.node_class, ExecutableBlock)) for e in elements):
            raise ValueError("elements must be a list of NodeT or ExecutableBlock")
        if not isinstance(id, str):
            raise ValueError("id must be a string")
        if not id.strip():
            raise ValueError("id cannot be empty or whitespace")

        self.id = id
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
            element_id = element.id

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


BlockT = TypeVar("BlockT", bound=ExecutableBlock)


# TODO_FUTURE: remove this class?
class ExecutableReference(Executable, Generic[ExecutableT, ContextT]):
    """A reference to a value in the execution_context."""

    def __init__(self, path: str):
        self.path = path

    async def execute(self, execution_context: ContextT) -> Any:
        """Get the referenced value from the execution_context."""
        return execution_context.get_value(self.path)
