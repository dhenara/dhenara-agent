import logging
from datetime import datetime
from typing import Any, ClassVar, Generic, TypeVar

from dhenara.agent.dsl.base import ComponentDefinition, ComponentExecutor
from dhenara.agent.dsl.flow import FlowBlock, FlowElement, FlowExecutionContext, FlowNode, FlowNodeDefinition
from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ExecutableBlock,
    ExecutableElement,
    ExecutionContext,
    NodeID,
)
from dhenara.agent.dsl.flow import FlowElement, FlowExecutionContext, FlowNode, FlowNodeDefinition
from dhenara.agent.observability import log_with_context, record_metric, trace_method
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseModel
from dhenara.ai.types.resource import ResourceConfig

ElementT = TypeVar("ElementT", bound=ExecutableElement)
BlockT = TypeVar("BlockT", bound=ExecutableBlock)
ContextT = TypeVar("ContextT", bound=ExecutionContext)
ComponentDefT = TypeVar("ComponentDefT", bound=ComponentDefinition)


class Flow(ComponentDefinition[FlowElement, FlowNode, FlowNodeDefinition, FlowExecutionContext]):
    node_class = FlowNode


class FlowExecutor(ComponentExecutor[FlowElement, FlowBlock, FlowExecutionContext, Flow]):
    block_class = FlowBlock
    context_class = FlowExecutionContext

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f"dhenara.agent.flow.{self.id}")

    @trace_method("execute_flow")
    async def execute(
        self,
        resource_config: ResourceConfig = None,
    ) -> dict[str, Any]:
        """Execute a flow with the given initial data."""
        # Record flow execution start
        start_time = datetime.now()
        log_with_context(self.logger, logging.INFO, f"Starting flow execution {self.id}", {"flow_id": str(self.id)})

        # Create the execution context
        execution_context = self.context_class(
            component_id=self.id,
            component_definition=self.definition,
            resource_config=resource_config,
            created_at=datetime.now(),
            run_context=self.run_context,
            artifact_manager=self.run_context.artifact_manager,
        )

        try:
            # Execute the flow
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
                attributes={"flow_id": str(self.id)},
            )

            # Record success
            record_metric(
                meter_name="dhenara.agent.flow",
                metric_name="flow_execution_success",
                value=1,
                attributes={"flow_id": str(self.id)},
            )

            log_with_context(
                self.logger,
                logging.INFO,
                f"Flow execution completed in {duration_sec:.2f}s",
                {"flow_id": str(self.id), "duration_sec": duration_sec},
            )

            return execution_context.results
        except Exception as e:
            # Record failure
            record_metric(
                meter_name="dhenara.agent.flow",
                metric_name="flow_execution_failure",
                value=1,
                attributes={"flow_id": str(self.id)},
            )

            log_with_context(
                self.logger,
                logging.ERROR,
                f"Flow execution failed: {e!s}",
                {"flow_id": str(self.id), "error": str(e)},
            )
            raise
