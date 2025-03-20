# dhenara/agent/flow/flow.py
from typing import Any, ClassVar, Generic, TypeVar, Union

from pydantic import Field

from dhenara.agent.dsl.base import (
    ExecutableBlock,
    ExecutableElement,
    ExecutableNode,
    ExecutableNodeDefinition,
    ExecutionContext,
)
from dhenara.agent.types.base import BaseModelABC

ElementT = TypeVar("ElementT", bound=ExecutableElement)
NodeT = TypeVar("NodeT", bound=ExecutableNode)  # Fixed name
NodeDefT = TypeVar("NodeDefT", bound=ExecutableNodeDefinition)  # Fixed name
ContextT = TypeVar("ContextT", bound=ExecutionContext)


class ComponentDefinition(BaseModelABC, Generic[ElementT, NodeT, NodeDefT, ContextT]):
    """Base class for an Executable definitions. ( ie a gorup of nodes)"""

    elements: list[ElementT] = Field(default_factory=list)
    node_class: ClassVar[type[NodeT]]

    def element(self, element: ElementT) -> ElementT:
        """Add an element to the flow."""
        self.elements.append(element)
        return self

    def node(
        self,
        id: str,  # noqa: A002
        definition: NodeDefT,
    ) -> "ComponentDefinition":
        """Add a node to the flow."""

        self.elements.append(self.node_class(id=id, definition=definition))
        return self

    def if_block(
        self,
        condition: str,
        then_branch: Union["ComponentDefinition", list[ElementT]],
        else_branch: Union["ComponentDefinition", list[ElementT]] | None = None,
    ) -> "ComponentDefinition":
        """Add a conditional branch to the flow."""
        from dhenara.agent.dsl.base.control import Conditional

        # Convert ComponentDefinition objects to their elements
        if isinstance(then_branch, ComponentDefinition):
            then_branch = then_branch.elements

        if else_branch is not None and isinstance(else_branch, ComponentDefinition):
            else_branch = else_branch.elements

        self.elements.append(Conditional(condition, then_branch, else_branch))
        return self

    def for_each_block(
        self,
        items: str,
        body: Union["ComponentDefinition", list[ElementT]],
        item_var: str = "item",
        index_var: str = "index",
        collect_results: bool = True,
        max_iterations: int | None = None,
    ) -> "ComponentDefinition":
        """Add a loop to the flow."""
        from dhenara.agent.dsl.base.control import ForEach

        # Convert ComponentDefinition object to its elements
        if isinstance(body, ComponentDefinition):
            body = body.elements

        self.elements.append(
            ForEach(
                items=items,
                body=body,
                item_var=item_var,
                index_var=index_var,
                collect_results=collect_results,
                max_iterations=max_iterations,
            )
        )
        return self

    async def execute(self, context: ContextT) -> dict[str, Any]:
        """Execute the flow in the given context."""
        block = ExecutableBlock(self.elements)
        await block.execute(context)
        return context.results
