import logging
from abc import abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import Field, field_validator

from dhenara.agent.dsl.base import (
    ComponentExeResultT,
    ContextT,
    ExecutableTypeEnum,
    NodeID,
    auto_converr_str_to_template,
)
from dhenara.agent.dsl.base.data.dad_template_engine import DADTemplateEngine
from dhenara.agent.dsl.base.utils.id_mixin import IdentifierValidationMixin, NavigationMixin
from dhenara.agent.dsl.events import EventType
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseModelABC
from dhenara.agent.types.defs import PLACEHOLDER
from dhenara.ai.types.genai.dhenara.request.data import ObjectTemplate

logger = logging.getLogger(__name__)

# Component registry initialization
component_executor_registry = None


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

    pre_events: list[EventType | str] | None = Field(
        default=None,
        description="Event need to be triggered before node execution.",
    )
    post_events: list[EventType | str] | None = Field(
        default_factory=lambda: [EventType.component_execution_completed],
        description="Event need to be triggered after node execution.",
    )

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

    variables: dict[str, Any | ObjectTemplate] = Field(
        default_factory=dict,
        description="Variables avaialbe in this flow, which can be used in nodes",
    )

    @property
    def trigger_pre_execute_input_required(self):
        return self.pre_events and EventType.component_input_required in self.pre_events

    @property
    def trigger_execution_completed(self):
        return self.post_events and EventType.component_execution_completed in self.post_events

    @field_validator("variables")
    @classmethod
    def validate_variables(cls, v):
        """Convert string variables to templates"""
        _vars = v.copy()
        for k, v in _vars.items():
            _vars[k] = auto_converr_str_to_template(v)
        return _vars

    def vars(self, variables=dict[str, Any]) -> "ComponentDefinition":
        """Add variables to the component."""
        if not isinstance(variables, dict):
            raise ValueError(f"Variables should be a dict not {type(variables)}")

        # Merge variables and validate them directly
        combined_vars = {**self.variables, **variables}
        self.variables = self.validate_variables(combined_vars)
        return self

    def update_vars(self, variables: dict | None = None, require_all: bool = False) -> None:
        self.variables = self.update_component_variables(
            current_variables=self.variables,
            new_variables=variables,
            require_all=require_all,
        )

    @classmethod
    def update_component_variables(
        cls,
        current_variables: dict,
        new_variables: dict | None = None,
        require_all: bool = False,
        disable_partial_key_checks: bool = False,
    ) -> dict:
        """
        Update variables with new values.

        Args:
            current_variables: The current variables dictionary
            new_variables: New variables to update with
            require_all: If True, require all variables to be provided (no partial updates)
            validate_fn: Optional validation function to call on the final variables

        Returns:
            Updated variables dictionary

        Raises:
            ValueError: If validation fails or unknown/missing variables
        """
        if not new_variables:
            return current_variables.copy()

        if require_all:
            # Check if all keys in new_variables are present in current_variables and no extra/missing keys
            if set(new_variables.keys()) != set(current_variables.keys()):
                extra_keys = set(new_variables.keys()) - set(current_variables.keys())
                missing_keys = set(current_variables.keys()) - set(new_variables.keys())
                error_msg = []
                if extra_keys:
                    error_msg.append(f"Extra variables provided: {extra_keys}")
                if missing_keys:
                    error_msg.append(f"Missing required variables: {missing_keys}")
                raise ValueError(", ".join(error_msg))

            updated_vars = new_variables.copy()
        else:
            if not disable_partial_key_checks:
                # Allow partial updates - only validate that provided keys exist
                extra_keys = set(new_variables.keys()) - set(current_variables.keys())
                if extra_keys:
                    raise ValueError(f"Unknown variables: {extra_keys}")

            # Update only the provided variables
            updated_vars = {**current_variables, **new_variables}

        return cls.validate_variables(updated_vars)

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
        elif hasattr(element, "true_branch") and element.true_branch:
            children = list(getattr(element.true_branch, "elements", []))
            if hasattr(element, "false_branch") and element.false_branch:
                children.extend(getattr(element.false_branch, "elements", []))
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
        elif hasattr(element, "true_branch") and element.true_branch:
            children = list(getattr(element.true_branch, "elements", []))
            if hasattr(element, "false_branch") and element.false_branch:
                children.extend(getattr(element.false_branch, "elements", []))
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

    # -------------------------------------------------------------------------
    def get_processed_component_variables(
        self,
        execution_context: ContextT,
    ) -> Any:
        component_variables = {}
        for var_name, var_value in self.variables.items():
            # Update the component variables
            _processed = self._process_component_variable(
                variable_name=var_name,
                variable_value=var_value,
                execution_context=execution_context,
            )
            component_variables[var_name] = _processed

        return component_variables

    def _process_component_variable(
        self,
        variable_name,
        variable_value,
        execution_context: ContextT,
    ):
        if isinstance(variable_value, ObjectTemplate):
            # Update the component variables
            _rendered = DADTemplateEngine.render_dad_template(
                template=variable_value,
                variables={},
                execution_context=execution_context,
            )
            return _rendered
        elif variable_name is PLACEHOLDER:
            raise ValueError(
                f"Error: {variable_name}: PLACEHOLDER should be replaced with valid values before processing variable."
            )
        elif variable_name is None:
            logger.warning(
                f"None value detected for component variable {variable_name} while processiing variable. "
                "Most likey this is uninterntional and will result in unexptected flow execution results"
            )
        else:
            # Allow all other values
            return variable_value

    # -------------------------------------------------------------------------
    def get_component_executor(self):
        """Get the component_executor for this component definition. This internally handles executor registry"""
        global component_executor_registry

        if component_executor_registry is None:
            from ._component_registry import ComponentExecutorRegistry

            component_executor_registry = ComponentExecutorRegistry()

        executor = component_executor_registry.get_executor(
            component_type=self.executable_type,
        )

        if executor is None:
            executor = component_executor_registry.register(
                component_type=self.executable_type,
                executor_class=self.get_executor_class(),
            )

        return executor

    @abstractmethod
    def get_executor_class(self):
        """Get the component_executor class for this component definition."""
        pass


ComponentDefT = TypeVar("ComponentDefT", bound=ComponentDefinition)
