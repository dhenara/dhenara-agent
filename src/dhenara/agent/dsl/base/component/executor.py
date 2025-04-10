import logging
from datetime import datetime
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import Field

from dhenara.agent.dsl.base import ComponentDefinition, ExecutableBlock, ExecutableElement, ExecutionContext, NodeID
from dhenara.agent.observability import log_with_context, record_metric
from dhenara.agent.observability.tracing import trace_method
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseModel

ElementT = TypeVar("ElementT", bound=ExecutableElement)
BlockT = TypeVar("BlockT", bound=ExecutableBlock)
ContextT = TypeVar("ContextT", bound=ExecutionContext)
ComponentDefT = TypeVar("ComponentDefT", bound=ComponentDefinition)


class ComponentExecutor(BaseModel, Generic[ElementT, BlockT, ContextT, ComponentDefT]):
    """Executor for Flow definitions."""

    id: NodeID = Field(...)
    definition: ComponentDefT = Field(...)

    # Concrete classes to use
    context_class: ClassVar[type[ContextT]]
    block_class: ClassVar[type[BlockT]]

    run_context: RunContext

    logger_path: str = "dhenara.dad.dsl.comp"
    logger: logging.Logger | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f"{self.logger_path}.{self.id}")

    # async def execute(
    #    self,
    # ) -> dict[str, Any]:
    #    """Execute a flow with the given initial data."""
    #    # Create the execution context

    #    execution_context = self.context_class(
    #        component_id=self.id,
    #        component_definition=self.definition,
    #        created_at=datetime.now(),
    #        run_context=self.run_context,
    #        artifact_manager=self.run_context.artifact_manager,
    #    )

    #    # Execute the flow
    #    block = self.block_class(self.definition.elements)
    #    await block.execute(
    #        execution_context=execution_context,
    #    )
    #    return execution_context.results

    @trace_method("execute_flow")
    async def execute(
        self,
        start_node_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute a flow with the given initial data, optionally starting from a specific node.

        Args:
            start_node_id: Optional node ID to start execution from
        """
        # Record flow execution start
        start_time = datetime.now()
        log_with_context(
            self.logger,
            logging.INFO,
            f"Starting flow execution {self.id}" + (f" from node {start_node_id}" if start_node_id else ""),
            {"flow_id": str(self.id), "start_node_id": start_node_id},
        )

        # Create the execution context
        execution_context = self.context_class(
            component_id=self.id,
            component_definition=self.definition,
            resource_config=self.run_context.resource_config,
            created_at=datetime.now(),
            run_context=self.run_context,
            artifact_manager=self.run_context.artifact_manager,
            start_node_id=start_node_id,
        )

        try:
            # Execute the flow from the specified node
            block = self.block_class(self.definition.elements)
            await block.execute(
                execution_context=execution_context,
            )

            # Record metrics
            end_time = datetime.now()
            duration_sec = (end_time - start_time).total_seconds()
            record_metric(
                meter_name="dhenara.agent.flow",
                metric_name="flow_execution_duration",
                value=duration_sec,
                metric_type="histogram",
                attributes={
                    "flow_id": str(self.id),
                    "is_rerun": str(self.run_context.is_rerun),
                    "start_node_id": start_node_id or "none",
                },
            )

            # Record success
            record_metric(
                meter_name="dhenara.agent.flow",
                metric_name="flow_execution_success",
                value=1,
                attributes={
                    "flow_id": str(self.id),
                    "is_rerun": str(self.run_context.is_rerun),
                },
            )

            log_with_context(
                self.logger,
                logging.INFO,
                f"Flow execution completed in {duration_sec:.2f}s",
                {
                    "flow_id": str(self.id),
                    "duration_sec": duration_sec,
                    "is_rerun": str(self.run_context.is_rerun),
                    "start_node_id": start_node_id or "none",
                },
            )

            return execution_context.results
        except Exception as e:
            # Record failure
            record_metric(
                meter_name="dhenara.agent.flow",
                metric_name="flow_execution_failure",
                value=1,
                attributes={
                    "flow_id": str(self.id),
                    "is_rerun": str(self.run_context.is_rerun),
                    "error": str(e),
                },
            )

            log_with_context(
                self.logger,
                logging.ERROR,
                f"Flow execution failed: {e!s}",
                {
                    "flow_id": str(self.id),
                    "error": str(e),
                    "is_rerun": str(self.run_context.is_rerun),
                    "start_node_id": start_node_id or "none",
                },
            )
            raise

    def get_ordered_node_ids(self) -> list[str]:
        """Get all node IDs in execution order."""
        elements, ids = self.definition._get_flattened_elements()
        return ids
