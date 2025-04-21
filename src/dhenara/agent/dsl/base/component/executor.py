import logging
from datetime import datetime
from typing import Any

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentTypeEnum,
    ContextT,
    ExecutableNode,
    ExecutableTypeEnum,
    ExecutionStatusEnum,
    NodeID,
)
from dhenara.agent.observability import log_with_context, record_metric
from dhenara.agent.observability.tracing.data.profile import ComponentTracingProfile
from dhenara.agent.observability.tracing.decorators.fns import trace_component
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseModelABC


class ComponentExecutor(BaseModelABC):
    """Executor for Flow definitions."""

    executable_type: ExecutableTypeEnum
    component_type: ComponentTypeEnum  # Purely for tracing and logging
    logger: logging.Logger | None = None

    _tracing_profile: ComponentTracingProfile | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f"dhenara.dad.dsl.{self.executable_type.value}")

        self._tracing_profile = ComponentTracingProfile()
        self._tracing_profile.component_type = self.component_type.value

    @trace_component()
    async def execute(
        self,
        component_id: NodeID,
        component_definition: ComponentDefinition,
        execution_context: ContextT | None = None,
        run_context: RunContext | None = None,
    ) -> ComponentExecutionResult:
        """Execute a flow with the given initial data, optionally starting from a specific node."""
        start_time = datetime.now()

        # Determine the proper start ID based on executable type and context
        start_id = None
        if run_context:
            if self.executable_type == ExecutableTypeEnum.agent and run_context.start_id_agent:
                start_id = run_context.start_id_agent
            elif self.executable_type == ExecutableTypeEnum.flow and run_context.start_id_flow:
                start_id = run_context.start_id_flow
            # elif self.executable_type == ExecutableTypeEnum.flow_node and run_context.start_id_flow_node:
            #    start_id = run_context.start_id_flow_node

        _logattribute = {
            "component_id": str(component_id),
            "component_type": self.component_type.value,
        }
        if start_id:
            _logattribute["start_id"] = start_id

        # Log execution start
        log_with_context(
            self.logger,
            logging.INFO,
            f"Starting {self.executable_type.value} execution {component_id}"
            + (f" from node {start_id}" if start_id else ""),
            _logattribute,
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
                start_id=start_id,
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
                start_id=start_id,
            )

        except Exception as e:
            import traceback

            # Get the full error hierarchy as a string
            error_trace = traceback.format_exc()

            # Handle execution failure
            is_rerun = run_context.is_rerun if run_context else False
            execution_result = component_definition.result_class(
                component_id=str(component_id),
                is_rerun=is_rerun,
                start_id=start_id,
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
                error=str(e),
                start_id=start_id,
            )

        # Return the component level result
        return execution_result

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

        execution_context.set_current_node(component_id)

        for element in component_definition.elements:
            element_start_time = datetime.now()

            if isinstance(element, ExecutableNode):
                # For regular nodes
                node = element
                start_id = execution_context.start_id
                start_execution = start_id is None or node.id == start_id

                # Log node execution
                log_level = logging.INFO if start_execution else logging.DEBUG
                log_with_context(
                    self.logger,
                    log_level,
                    f"{'Executing' if start_execution else 'Skipping'} node {node.id}",
                    {"node_id": str(node.id), "component_id": str(component_id)},
                )

                if start_execution:
                    # If we should execute this node
                    if start_id == node.id:
                        # Clear the start_id since we found it
                        execution_context.start_id = None
                        self.logger.info(f"Starting execution from node {node.id}")

                    result = await node.execute(execution_context)
                else:
                    # Load from previous run
                    result = await node.load_from_previous_run(execution_context)

                results.append(result)

                # Log node completion
                element_duration = (datetime.now() - element_start_time).total_seconds()
                log_with_context(
                    self.logger,
                    logging.INFO,
                    (
                        f"Node {node.id} {'execution' if start_execution else 'loading'} "
                        "completed in {element_duration:.2f}s"
                    ),
                    {"node_id": str(node.id), "duration_sec": element_duration},
                )

            else:
                # For child components
                subcomponent = element
                self.logger.info(f"Processing child component {subcomponent.id}")

                # Create the component execution context
                component_execution_context = subcomponent.definition.context_class(
                    component_id=subcomponent.id,
                    component_definition=subcomponent.definition,
                    created_at=datetime.now(),
                    run_context=execution_context.run_context,
                    parent=execution_context,
                )

                # Check if this is where we should start
                start_id = execution_context.start_id
                start_execution = start_id is None or subcomponent.id == start_id

                if start_execution:
                    if start_id == subcomponent.id:
                        # We found our starting component, clear the start_id
                        execution_context.start_id = None
                        self.logger.info(f"Starting execution from component {subcomponent.id}")

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
                        f"Component {subcomponent.id} {'execution' if start_execution else 'loading'} "
                        "completed in {element_duration:.2f}s"
                    ),
                    {"component_id": str(subcomponent.id), "duration_sec": element_duration},
                )

        return results

    def _record_successful_execution(self, component_id, duration_sec, is_rerun, start_id):
        """Record metrics for successful execution."""
        record_metric(
            meter_name=f"dhenara.dad.{self.executable_type}",
            metric_name=f"{self.executable_type}_execution_duration",
            value=duration_sec,
            metric_type="histogram",
            attributes={
                f"{self.executable_type}_id": str(component_id),
                "is_rerun": str(is_rerun),
                "start_id": start_id or "none",
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
                "start_id": start_id or "none",
            },
        )

    def _record_failed_execution(self, component_id, is_rerun, error, start_id):
        """Record metrics for failed execution."""
        record_metric(
            meter_name=f"dhenara.dad.{self.executable_type}",
            metric_name=f"{self.executable_type}_execution_failure",
            value=1,
            attributes={
                f"{self.executable_type}_id": str(component_id),
                "is_rerun": str(is_rerun),
                "error": error,
            },
        )

        log_with_context(
            self.logger,
            logging.ERROR,
            f"{self.executable_type.title()} execution failed: {error}",
            {
                f"{self.executable_type}_id": str(component_id),
                "error": error,
                "is_rerun": str(is_rerun),
                "start_id": start_id or "none",
            },
        )
