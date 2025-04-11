from typing import Any

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentExecutor,
    ComponentTypeEnum,
)
from dhenara.agent.dsl.components.flow import FlowBlock, FlowElement, FlowExecutionContext, FlowNode, FlowNodeDefinition
from dhenara.agent.observability.tracing.decorators.fns2 import trace_method


class FlowExecutionResult(ComponentExecutionResult):
    component_type: ComponentTypeEnum = ComponentTypeEnum.flow


class Flow(ComponentDefinition[FlowElement, FlowNode, FlowNodeDefinition, FlowExecutionContext]):
    component_type: ComponentTypeEnum = ComponentTypeEnum.flow
    node_class = FlowNode


class FlowExecutor(ComponentExecutor[FlowElement, FlowBlock, FlowExecutionContext, Flow, FlowExecutionResult]):
    component_type: ComponentTypeEnum = ComponentTypeEnum.flow
    block_class = FlowBlock
    context_class = FlowExecutionContext
    result_class = FlowExecutionResult
    logger_path: str = "dhenara.dad.flow"

    # Deinfe abstractmethod with proper trace name
    @trace_method("execute_flow")
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
