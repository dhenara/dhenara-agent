import datetime
from typing import Any, ClassVar, Generic, TypeVar, Union

from pydantic import Field

from dhenara.agent.dsl.base import (
    Conditional,
    ContextT,
    ExecutableNodeDefinition,
    ExecutableT,
    ExecutableTypeEnum,
    ForEach,
    NodeDefT,
    NodeID,
    NodeT,
)
from dhenara.agent.dsl.base.utils.id_mixin import IdentifierValidationMixin, NavigationMixin
from dhenara.agent.types.base import BaseModelABC


class ComponentDefinition(
    BaseModelABC,
    Generic[ExecutableT, NodeT, ContextT],
    IdentifierValidationMixin[ExecutableT],
    NavigationMixin,
):
    """Base class for Executable definitions."""

    executable_type: ExecutableTypeEnum
    elements: list[NodeT | Any] = Field(default_factory=list)
    # elements: list[NodeT | "ComponentDefinition"] = Field(default_factory=list)

    node_class: ClassVar[type[NodeT]]

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
    # Factory methods for creating components
    def node(
        self,
        id: str,  # noqa: A002
        definition: NodeDefT,
    ) -> "ComponentDefinition":
        """Add a node to the flow."""

        if not isinstance(definition, ExecutableNodeDefinition) and definition.executable_type == self.executable_type:
            raise ValueError(
                f"Unsupported type for definition: {type(definition)}. "
                f"Expected a {self.executable_type}-NodeDefinition."
            )

        _node = self.node_class(id=id, definition=definition)
        self.elements.append(_node)
        return self

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
        execution_context: ContextT,
        component_id: NodeID | None = None,
    ) -> list[Any]:
        """Execute all elements in this block sequentially.

        If start_component_id is specified, skip elements until the starting component is found.
        """
        results = []

        # NOTE: The component is the `top-level` heirrachy of the element, there won't be an executor for that
        # Thus the individual elements should be executed here
        for element in self.elements:
            if isinstance(element, ComponentDefinition):
                # There is a child component in elements
                if component_id is None:
                    raise ValueError("component_id should be set for child component")

                component = element
                execution_context.logger.info(f"Found a Child component with ID {component_id}")

                start_component_id = getattr(execution_context, "start_component_id", None)
                start_execution = start_component_id is None  # Start immediately if no start_component_id

                # If a element a component, an execution context need to be created here
                component_execution_context = self.context_class(
                    component_id=self.id,
                    component_definition=self.definition,
                    resource_config=self.run_context.resource_config,
                    created_at=datetime.now(),
                    run_context=self.run_context,
                    artifact_manager=self.run_context.artifact_manager,
                    start_node_id=start_component_id,
                    parent=execution_context,
                )

                # Check if this is the component we should start from
                if not start_execution and component_id == start_component_id:
                    # Found our starting point, begin execution
                    start_execution = True
                    component_execution_context.logger.info(f"Starting execution from compoent {start_component_id}")

                if start_execution:
                    component_execution_context.set_current_component(component_id)
                    # compnent_executor = self.get_compnent_executor()
                    result = await component.execute(
                        component_id=None,
                        execution_context=component_execution_context,
                    )
                    results.append(result)
                else:
                    result = await component.load_from_previous_run(component_execution_context)
                    results.append(result)
            else:
                # For nodes, pass the incoming execution context
                node = element
                start_node_id = getattr(execution_context, "start_node_id", None)
                start_execution = start_node_id is None  # Start immediately if no start_node_id

                # Check if this is the node we should start from
                if not start_execution and node.id == start_node_id:
                    # Found our starting point, begin execution
                    start_execution = True
                    execution_context.logger.info(f"Starting execution from node {start_node_id}")

                if start_execution:
                    result = await node.execute(execution_context)
                    results.append(result)
                else:
                    result = await node.load_from_previous_run(execution_context)
                    results.append(result)

        return results


ComponentDefT = TypeVar("ComponentDefT", bound=ComponentDefinition)
