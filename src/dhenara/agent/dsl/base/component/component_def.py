from abc import abstractmethod
from typing import Any, ClassVar, Generic, TypeVar, Union

from pydantic import Field

from dhenara.agent.dsl.base import (
    ComponentExeResultT,
    Conditional,
    ContextT,
    ExecutableTypeEnum,
    ForEach,
    NodeID,
)
from dhenara.agent.dsl.base.utils.id_mixin import IdentifierValidationMixin, NavigationMixin
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseModelABC


class ComponentDefinition(
    BaseModelABC,
    # Executable,
    IdentifierValidationMixin,
    NavigationMixin,
    Generic[ContextT, ComponentExeResultT],
):
    """Base class for Executable definitions."""

    elements: list[Any] = Field(default_factory=list)
    # elements: list[NodeT | "ComponentDefinition"] = Field(default_factory=list)

    executable_type: ExecutableTypeEnum
    context_class: ClassVar[type[ContextT]]
    result_class: ClassVar[type[ComponentExeResultT]]
    logger_path: str = "dhenara.dad.component"

    root_id: str | None = Field(
        default=None,
        description=(
            "Id if this is a root component. "
            "Do not set ID for any other componets, as id should be assigned when added to a node"
        ),
    )
    description: str | None = Field(
        default=None,
        description="Detailed Description about this component",
    )
    io_description: str | None = Field(
        default=None,
        description=(
            "Description about the input and output of this agent. "
            "Useful in multli-agent system to know more about an agent"
        ),
    )

    # -------------------------------------------------------------------------
    # Common implementation of abstract methods used by mixins
    def _get_element_identifier(self, element) -> str:
        """Extract identifier from element."""
        if hasattr(element, "id"):
            return element.id
        return getattr(element, "identifier", str(id(element)))

    def _get_element_children(self, element) -> list:
        """Get children from element."""
        # For nodes with subflows or nested elements
        if hasattr(element, "subflow") and element.subflow:
            return element.subflow.elements
        # For conditional branches
        elif hasattr(element, "then_branch") and element.then_branch:
            children = list(getattr(element.then_branch, "elements", []))
            if hasattr(element, "else_branch") and element.else_branch:
                children.extend(getattr(element.else_branch, "elements", []))
            return children
        # For other element types
        return getattr(element, "elements", [])

    def _get_top_level_elements(self) -> list:
        """Get all top-level elements."""
        return self.elements

    # @field_validator("elements")
    # @classmethod
    # def validate_element_order(cls, elements):
    #    """Validate element ordering if applicable."""
    #    if elements and hasattr(elements[0], "order"):
    #        orders = [element.order for element in elements]
    #        expected_orders = list(range(len(elements)))
    #        if orders != expected_orders:
    #            raise ValueError("Element orders must be sequential starting from 0 within each component")
    #    return elements

    # Implement abstract methods from the mixin
    def _get_element_identifier(self, element) -> str:
        """Extract identifier from element."""
        if hasattr(element, "id"):
            return element.id
        return getattr(element, "identifier", str(id(element)))

    def _get_element_children(self, element) -> list:
        """Get children from element."""
        # For nodes with subflows or nested elements
        if hasattr(element, "subflow") and element.subflow:
            return element.subflow.elements
        # For conditional branches
        elif hasattr(element, "then_branch") and element.then_branch:
            children = list(getattr(element.then_branch, "elements", []))
            if hasattr(element, "else_branch") and element.else_branch:
                children.extend(getattr(element.else_branch, "elements", []))
            return children
        # For other element types
        return getattr(element, "elements", [])

    def _get_top_level_elements(self) -> list:
        """Get all top-level elements."""
        return self.elements

    # -------------------------------------------------------------------------

    # TODO: Cleanup
    def conditional(
        self,
        id: str,  # noqa: A002
        condition: str,
        then_branch: Union["ComponentDefinition",],
        # else_id: str,
        else_branch: Union["ComponentDefinition",] | None = None,
    ) -> "ComponentDefinition":
        """Add a conditional branch to the flow."""

        # Convert ComponentDefinition objects to their elements
        if isinstance(then_branch, ComponentDefinition):
            then_branch = then_branch.elements

        if else_branch is not None and isinstance(else_branch, ComponentDefinition):
            else_branch = else_branch.elements

        self.elements.append(Conditional(condition, then_branch, else_branch))
        return self

    def for_each(
        self,
        id: str,  # noqa: A002
        body,  #: Union["ComponentDefinition", BlockT, NodeT],
        items: str,
        item_var: str = "item",
        index_var: str = "index",
        collect_results: bool = True,
        max_iterations: int | None = None,
    ) -> "ComponentDefinition":
        """Add a loop to the flow."""

        if isinstance(body, type(self)):
            _body_blcok = self.as_block(id=id)
        elif isinstance(body, self.block_class):
            _body_blcok = body
        elif isinstance(body, self.node_class):
            _body_blcok = self.block_class(id=id, elements=[body])
        else:
            raise ValueError(
                f"Unsupported type for body: {type(body)}. "
                f"Expected {type(self)} or {self.block_class} or {self.node_class}."
            )

        # Convert ComponentDefinition object to its elements
        _foreach = ForEach(
            items=items,
            body=_body_blcok,
            item_var=item_var,
            index_var=index_var,
            collect_results=collect_results,
            max_iterations=max_iterations,
        )
        self.elements.append(_foreach)
        return self

    async def execute(
        self,
        component_id: NodeID,
        execution_context: ContextT,
        run_context: RunContext | None = None,
    ) -> Any:
        return await self._execute(
            component_id=component_id,
            execution_context=execution_context,
            run_context=run_context,
        )

    async def _execute(
        self,
        component_id: NodeID,
        execution_context: ContextT,
        run_context: RunContext | None = None,
    ) -> Any:
        component_executor = self.get_component_executor()

        result = await component_executor.execute(
            component_id=component_id,
            component_definition=self,
            execution_context=execution_context,
            run_context=run_context,
        )
        return result

    @abstractmethod
    def get_component_executor(self):
        """Get the component_executor for this component definition. This internally handles executor registry"""
        pass


ComponentDefT = TypeVar("ComponentDefT", bound=ComponentDefinition)
