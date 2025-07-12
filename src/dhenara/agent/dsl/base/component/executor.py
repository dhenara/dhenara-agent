import logging
from datetime import datetime
from typing import Any

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentInput,
    ComponentInputT,
    ComponentTypeEnum,
    ContextT,
    ExecutableNode,
    ExecutableTypeEnum,
    ExecutionContext,
    ExecutionStatusEnum,
    NodeID,
)
from dhenara.agent.dsl.events import (
    ComponentExecutionCompletedEvent,
    ComponentInputRequiredEvent,
    TraceUpdateEvent,
)
from dhenara.agent.observability import log_with_context, record_metric
from dhenara.agent.observability.tracing import get_current_trace_id
from dhenara.agent.observability.tracing.data.profile import ComponentTracingProfile
from dhenara.agent.observability.tracing.decorators.fns import trace_component
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseModelABC

logger = logging.getLogger(__name__)


class ComponentExecutor(BaseModelABC):
    """Executor for Flow definitions."""

    executable_type: ExecutableTypeEnum
    component_type: ComponentTypeEnum  # Purely for tracing and logging
    input_model: ComponentInputT
    logger: logging.Logger | None = None

    _tracing_profile: ComponentTracingProfile | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f"dhenara.dad.dsl.{self.executable_type.value}")

        self._tracing_profile = ComponentTracingProfile()
        self._tracing_profile.component_type = self.component_type.value

    async def get_input_for_component(
        self,
        component_id: NodeID,
        component_definition: ComponentDefinition,
        execution_context: ExecutionContext,
    ) -> ComponentInput:
        """Get input for a component, trying static inputs first then event handlers."""
        # Check static inputs first
        if component_id in execution_context.run_context.static_inputs:
            log_with_context(self.logger, logging.DEBUG, f"Using static input for component {component_id}")
            return execution_context.run_context.static_inputs[component_id]

        if component_definition.trigger_pre_execute_input_required:
            component_input = await self.tirgger_event_component_input_required(
                component_id=component_id,
                component_definition=component_definition,
                execution_context=execution_context,
            )
            return component_input

        log_with_context(self.logger, logging.DEBUG, f"Failed to fetch inputs for component {component_id}")
        return None

    # Inbuild  events
    async def tirgger_event_component_input_required(
        self,
        component_id: NodeID,
        component_definition: ComponentDefinition,
        execution_context: ExecutionContext,
    ) -> ComponentInput:
        # Request input via event
        event = ComponentInputRequiredEvent(
            component_id=component_id,
            component_type=component_definition.executable_type,
            component_def_variables=component_definition.variables,
        )
        await execution_context.run_context.event_bus.publish(event)

        component_input = None

        # Check if any handler provided input
        if event.handled and event.component_input:
            if isinstance(event.component_input, dict):
                try:
                    component_input = self.input_model(**event.component_input)
                except Exception as e:
                    logger.error(f"{component_id}: Error while validation component input dict vai event. {e}")

            elif isinstance(event.component_input, self.input_model):
                component_input = event.component_input
            else:
                logger.error(f"{component_id}: Invalid component_input type {type(component_input)}")

            logger.debug(f"{component_id}: component input via event {event.type} is {component_input}")
        else:
            # No input provided by any handler
            logger.error(f"{component_id}: No input provided for component via event {event.type}")

        return component_input

    @trace_component()
    async def execute(
        self,
        component_id: NodeID,
        component_definition: ComponentDefinition,
        execution_context: ContextT | None = None,
        run_context: RunContext | None = None,
    ) -> ComponentExecutionResult:
        """Execute a flow with the given initial data, optionally starting from a specific component."""

        # run_context !=None -> Its the root level execution
        if run_context:
            trace_id = get_current_trace_id()
            execution_id = run_context.execution_id

            if trace_id and execution_id:
                event = TraceUpdateEvent(trace_id=trace_id, execution_id=execution_id)
                await run_context.event_bus.publish(event)

        start_time = datetime.now()

        _logattribute = {
            "component_id": str(component_id),
            "component_type": self.component_type.value,
        }
        start_hierarchy_path = run_context.start_hierarchy_path if run_context else None

        if start_hierarchy_path:
            _logattribute["start_hierarchy_path"] = start_hierarchy_path

        # Log execution start
        log_with_context(
            self.logger,
            logging.INFO,
            f"Starting {self.executable_type.value} execution {component_id}"
            + (f" from {start_hierarchy_path}" if start_hierarchy_path else ""),
            _logattribute,
        )

        component_input = None
        if component_definition.trigger_pre_execute_input_required:
            component_input = await self.get_input_for_component(
                component_id=component_id,
                component_definition=component_definition,
                execution_context=execution_context,
            )

            log_with_context(
                self.logger, logging.DEBUG, "Component Input received", {"component_id": str(component_id)}
            )

            if not isinstance(component_input, self.input_model):
                log_with_context(
                    self.logger,
                    logging.ERROR,
                    f"Input validation failed. Expected {self.input_model} but got {type(component_input)}",
                    {"component_id": str(component_id)},
                )
                raise ValueError(
                    f"Input validation failed. Expects type is {self.input_model}, "
                    f"actual typs is {type(component_input)}"
                )

        try:
            # Create execution context if not priovided
            # This happens only for the top level component
            if execution_context is None:
                execution_context = component_definition.context_class(
                    component_id=component_id,
                    component_definition=component_definition,
                    created_at=datetime.now(),
                    run_context=run_context,
                    parent=None,
                )

            await self.load_initial_input_from_run_ctx(component_definition, execution_context)

            # Update component_inputs
            if component_input:
                # NOTE: Updating variables in component_definition won't take effect, as execution context had
                # already copied the component_definition variables
                updated_vars = ComponentDefinition.update_component_variables(
                    current_variables=execution_context.component_variables,
                    new_variables=component_input.component_variables,
                    require_all=False,
                )
                execution_context.component_variables = updated_vars
                logger.debug(
                    f"Updated component_variables with values from component_input. "
                    f"Variable keys are {updated_vars.keys()}"
                )

            # Execute all elements in the component
            await self.execute_all_elements(
                component_id=component_id,
                component_definition=component_definition,
                execution_context=execution_context,
            )

            execution_context.execution_status = ExecutionStatusEnum.COMPLETED
            is_rerun = execution_context.run_context.is_rerun

            # Create the execution result
            execution_result = component_definition.result_class(
                component_id=str(component_id),
                is_rerun=is_rerun,
                start_hierarchy_path=start_hierarchy_path,
                execution_status=execution_context.execution_status,
                execution_results=execution_context.execution_results,
                error=execution_context.execution_failed_message,
                metadata=execution_context.metadata,
                created_at=execution_context.created_at,
                updated_at=execution_context.updated_at,
                completed_at=execution_context.completed_at,
            )

            # Record execution metrics
            end_time = datetime.now()
            duration_sec = (end_time - start_time).total_seconds()
            self._record_successful_execution(
                component_id=component_id,
                duration_sec=duration_sec,
                is_rerun=is_rerun,
                start_hierarchy_path=start_hierarchy_path,
            )

            if component_definition.trigger_execution_completed:
                event = ComponentExecutionCompletedEvent(
                    component_id=component_id,
                    component_type=component_definition.executable_type,
                    component_outcome=None,  # TODO_FUTURE
                )
                await execution_context.run_context.event_bus.publish(event)

        except Exception as e:
            import traceback

            # Get the full error hierarchy as a string
            error_trace = traceback.format_exc()

            # Handle execution failure
            is_rerun = run_context.is_rerun if run_context else False
            execution_result = component_definition.result_class(
                component_id=str(component_id),
                is_rerun=is_rerun,
                start_hierarchy_path=start_hierarchy_path,
                execution_status=ExecutionStatusEnum.FAILED,
                execution_results={},
                error=f"Error while executing {self.executable_type}: {e}",
                metadata={"error_trace": error_trace},
                created_at=datetime.now(),
                updated_at=None,
                completed_at=None,
            )

            self._record_failed_execution(
                component_id=component_id,
                is_rerun=is_rerun,
                e=e,
                start_hierarchy_path=start_hierarchy_path,
            )

        # Return the component level result
        return execution_result

    async def load_initial_input_from_run_ctx(
        self,
        component_definition: ComponentDefinition,
        execution_context: ExecutionContext,
    ) -> ComponentInput:
        """Get input for a component, trying static inputs first then event handlers."""
        # Check static inputs first
        initial_component_variables = execution_context.run_context.initial_inputs.get("component_variables", {})

        if initial_component_variables:
            # NOTE: Updating variables in component_definition won't take effect, as execution context had
            # already copied the component_definition variables
            updated_vars = ComponentDefinition.update_component_variables(
                current_variables=component_definition.variables,
                new_variables=initial_component_variables,
                require_all=False,
                # TODO_FUTURE: P_LOW: enable this check by implementing heirarcy based roots in initial inputs
                disable_partial_key_checks=True,
            )
            execution_context.component_variables = updated_vars
            logger.debug(
                f"Loaded initial component_variables from run context. Variable keys are {updated_vars.keys()}"
            )

    def get_ordered_node_ids(
        self,
        component_definition: ComponentDefinition,
    ) -> list[str]:
        """Get all node IDs in execution order."""
        elements, ids = component_definition._get_flattened_elements()
        return ids

    async def execute_all_elements(
        self,
        component_id: str,
        component_definition: ComponentDefinition,
        execution_context: ContextT,
    ) -> list[Any]:
        """Execute all elements in this component sequentially."""
        results = []

        for element in component_definition.elements:
            element_start_time = datetime.now()
            if isinstance(element, ExecutableNode):
                # For regular nodes
                node = element

                # Set current node in the context
                execution_context.set_current_node(node.id)

                # Check if this is where we should start
                # NOTE: cache should_execute into a variable as it will reset the run context hierarchy upon hitting the
                # start_hierarchy_path

                should_execute = execution_context.should_execute
                if should_execute:
                    # Log node execution
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"Executing node {node.id}",
                        {"node_id": str(node.id), "component_id": str(component_id)},
                    )

                    result = await node.execute(execution_context)
                else:
                    # Loading from previous run instead of executing
                    log_with_context(
                        self.logger,
                        logging.DEBUG,
                        f"Skipping node {node.id}, loading from previous run",
                        {"node_id": str(node.id), "component_id": str(component_id)},
                    )
                    result = await node.load_from_previous_run(execution_context)

                results.append(result)

                # Log node completion
                element_duration = (datetime.now() - element_start_time).total_seconds()
                log_with_context(
                    self.logger,
                    logging.INFO,
                    (
                        f"Node {node.id} {'execution' if should_execute else 'loading'} "
                        "completed in {element_duration:.2f}s"
                    ),
                    {"node_id": str(node.id), "duration_sec": element_duration},
                )

            else:
                # For child components
                subcomponent = element
                self.logger.info(f"Processing child component {subcomponent.id}")

                # Set current node in the context
                execution_context.set_current_subcomponent(subcomponent.id)

                # INFO: We will always execute the subcomponent. There is no load_from_previous_run()
                # fn for subcomponents, as we don't save the subcomponent results in a result.json file.
                # When the subcomponent is executed, it will load its children node's results, and thus form the
                # complete result that component.

                # But still call the should_execute() method to correctly reset the hierarchy path if in case
                # the start_hierarchy_path is the current subcomponent
                should_execute = execution_context.should_execute

                component_variables = subcomponent.definition.get_processed_component_variables(execution_context)

                # Create the component execution context
                component_execution_context = subcomponent.definition.context_class(
                    component_id=subcomponent.id,
                    component_definition=subcomponent.definition,
                    created_at=datetime.now(),
                    run_context=execution_context.run_context,
                    parent=execution_context,
                    component_variables=component_variables,
                )

                if True:  # See comments above
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"Executing sub-component {subcomponent.id}",
                        {"node_id": "NA", "component_id": str(component_id)},
                    )

                    result = await subcomponent.execute(component_execution_context)
                else:
                    result = await subcomponent.load_from_previous_run(component_execution_context)

                results.append(result)

                # Log component completion
                element_duration = (datetime.now() - element_start_time).total_seconds()
                log_with_context(
                    self.logger,
                    logging.INFO,
                    (
                        f"Component {subcomponent.id} {'execution' if should_execute else 'loading'} "
                        "completed in {element_duration:.2f}s"
                    ),
                    {"component_id": str(subcomponent.id), "duration_sec": element_duration},
                )

        return results

    def _record_successful_execution(self, component_id, duration_sec, is_rerun, start_hierarchy_path):
        """Record metrics for successful execution."""
        record_metric(
            meter_name=f"dhenara.dad.{self.executable_type}",
            metric_name=f"{self.executable_type}_execution_duration",
            value=duration_sec,
            metric_type="histogram",
            attributes={
                f"{self.executable_type}_id": str(component_id),
                "is_rerun": str(is_rerun),
                "start_hierarchy_path": start_hierarchy_path or "none",
            },
        )

        record_metric(
            meter_name=f"dhenara.dad.{self.executable_type}",
            metric_name=f"{self.executable_type}_execution_success",
            value=1,
            attributes={
                f"{self.executable_type}_id": str(component_id),
                "is_rerun": str(is_rerun),
            },
        )

        log_with_context(
            self.logger,
            logging.INFO,
            f"{self.executable_type.title()} execution completed in {duration_sec:.2f}s",
            {
                f"{self.executable_type}_id": str(component_id),
                "duration_sec": duration_sec,
                "is_rerun": str(is_rerun),
                "start_hierarchy_path": start_hierarchy_path or "none",
            },
        )

    def _record_failed_execution(self, component_id, is_rerun, e, start_hierarchy_path):
        """Record metrics for failed execution."""
        record_metric(
            meter_name=f"dhenara.dad.{self.executable_type}",
            metric_name=f"{self.executable_type}_execution_failure",
            value=1,
            attributes={
                f"{self.executable_type}_id": str(component_id),
                "is_rerun": str(is_rerun),
                "error": str(e),
            },
        )

        log_with_context(
            self.logger,
            logging.ERROR,
            f"{self.executable_type.title()} execution failed: {e}",
            {
                f"{self.executable_type}_id": str(component_id),
                "error": str(e),
                "is_rerun": str(is_rerun),
                "start_hierarchy_path": start_hierarchy_path or "none",
            },
            exception=e,
        )
