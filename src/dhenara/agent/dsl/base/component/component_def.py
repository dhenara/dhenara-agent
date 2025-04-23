from abc import abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import Field

from dhenara.agent.dsl.base import (
    ComponentExeResultT,
    ContextT,
    ExecutableTypeEnum,
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
            "Do not set ID for any other componets, as id should be assigned when added as al element"
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
        # For elements with subflows or nested elements
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
        # For elements with subflows or nested elements
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
    async def execute(
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

    # -------------------------------------------------------------------------
    async def load_from_previous_run(
        self,
        component_id: NodeID,
        execution_context: ContextT,
    ) -> Any:
        raise ValueError(
            "Loading from previous run is not supported for component as we don't save component results in artifacts."
            "Use execute() fn to load from previous results as "
            "they will load_from_previous_run in the nodes and from the component results"
        )

        result_data = await execution_context.load_from_previous_run(copy_artifacts=True)

        if result_data:
            try:
                result = self.result_class(**result_data)
                # Set the result in the execution context
                execution_context.set_result(component_id, result)

                # TODO_FUTURE: record for tracing ?
                return result
            except Exception as e:
                execution_context.logger.error(f"Failed to load previous run data for component {component_id}: {e}")
                return None
        else:
            execution_context.logger.error(
                f"Falied to load data from previous execution result artifacts for component {component_id}"
            )
            return None

    @abstractmethod
    def get_component_executor(self):
        """Get the component_executor for this component definition. This internally handles executor registry"""
        pass


ComponentDefT = TypeVar("ComponentDefT", bound=ComponentDefinition)
