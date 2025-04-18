import logging
from abc import abstractmethod
from datetime import datetime
from typing import Any, ClassVar, Generic

from pydantic import Field

from dhenara.agent.dsl.base import ContextT, ExecutableT, ExecutableTypeEnum, ExecutionStatusEnum, NodeID
from dhenara.agent.observability import log_with_context, record_metric
from dhenara.agent.observability.tracing import trace_method
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseModelABC

from .comp_exe_result import ComponentExeResultT
from .component_def import ComponentDefT


class ComponentExecutor(
    BaseModelABC,
    Generic[
        ExecutableT,
        ContextT,
        ComponentDefT,
        ComponentExeResultT,
    ],
):
    """Executor for Flow definitions."""

    executable_type: ExecutableTypeEnum

    id: NodeID = Field(...)
    definition: ComponentDefT = Field(...)

    # Concrete classes to use
    context_class: ClassVar[type[ContextT]]
    result_class: ClassVar[type[ComponentExeResultT]]

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

    # NOTE: Defining exeute as an abstract class for imposing proper trace names in derived class
    @abstractmethod
    @trace_method("execute_{executable_type}")
    async def execute(
        self,
        start_node_id: str | None = None,
        parent_execution_context=None,
    ) -> dict[str, Any]:
        _result = await self._execute(
            start_node_id=start_node_id,
            parent_execution_context=parent_execution_context,
        )
        return _result

    async def _execute(
        self,
        start_node_id: str | None = None,
        parent_execution_context=None,
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
            f"Starting {self.executable_type.value} execution {self.id}"
            + (f" from node {start_node_id}" if start_node_id else ""),
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
            parent=parent_execution_context,
        )

        try:
            # block = self.definition.as_block(id=self.id)
            # await block.execute(
            #    execution_context=execution_context,
            # )

            await self.definition.execute(
                execution_context=execution_context,
            )
            execution_context.execution_status = ExecutionStatusEnum.COMPLETED

            execution_result = self.result_class(
                component_id=str(self.id),
                is_rerun=self.run_context.is_rerun,
                start_node_id=start_node_id,
                execution_status=execution_context.execution_status,
                execution_results=execution_context.execution_results,
                error=execution_context.execution_failed_message,
                metadata=execution_context.metadata,
                created_at=execution_context.created_at,
                updated_at=execution_context.updated_at,
                completed_at=execution_context.completed_at,
            )

            # TODO: Record with artifact manager
            # Do no duplicate execution results as they are already available in nodes

            # Record metrics
            end_time = datetime.now()
            duration_sec = (end_time - start_time).total_seconds()
            record_metric(
                meter_name=f"dhenara.dad.{self.definition.executable_type}",
                metric_name=f"{self.definition.executable_type}_execution_duration",
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
                meter_name=f"dhenara.dad.{self.definition.executable_type}",
                metric_name=f"{self.definition.executable_type}_execution_duration",
                value=1,
                attributes={
                    f"{self.definition.executable_type}_id": str(self.id),
                    "is_rerun": str(self.run_context.is_rerun),
                },
            )

            log_with_context(
                self.logger,
                logging.INFO,
                f"{self.definition.executable_type.title()} execution completed in {duration_sec:.2f}s",
                {
                    f"{self.definition.executable_type}_id": str(self.id),
                    "duration_sec": duration_sec,
                    "is_rerun": str(self.run_context.is_rerun),
                    "start_node_id": start_node_id or "none",
                },
            )

        except Exception as e:
            execution_result = self.result_class(
                component_id=str(self.id),
                is_rerun=self.run_context.is_rerun,
                start_node_id=start_node_id,
                execution_status=ExecutionStatusEnum.FAILED,
                execution_results={},
                error=f"Error while executing {self.definition.executable_type}: {e}",
                metadata={},
                created_at=datetime.now(),
                updated_at=None,
                completed_at=None,
            )

            # Record failure
            record_metric(
                meter_name=f"dhenara.dad.{self.definition.executable_type}",
                metric_name=f"{self.definition.executable_type}_execution_duration",
                value=1,
                attributes={
                    f"{self.definition.executable_type}_id": str(self.id),
                    "is_rerun": str(self.run_context.is_rerun),
                    "error": str(e),
                },
            )

            log_with_context(
                self.logger,
                logging.ERROR,
                f"{self.definition.executable_type.title()} execution failed: {e!s}",
                {
                    f"{self.definition.executable_type}_id": str(self.id),
                    "error": str(e),
                    "is_rerun": str(self.run_context.is_rerun),
                    "start_node_id": start_node_id or "none",
                },
            )

        # Return the component level result
        return execution_result

    def get_ordered_node_ids(self) -> list[str]:
        """Get all node IDs in execution order."""
        elements, ids = self.definition._get_flattened_elements()
        return ids
