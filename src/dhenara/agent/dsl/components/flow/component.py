from typing import Any

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentExecutor,
    ExecutableTypeEnum,
)
from dhenara.agent.dsl.components.flow import FlowBlock, FlowExecutable, FlowExecutionContext, FlowNode
from dhenara.agent.observability.tracing.decorators.fns2 import trace_method


class FlowExecutionResult(ComponentExecutionResult):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow


class Flow(ComponentDefinition[FlowExecutable, FlowNode, FlowBlock, FlowExecutionContext]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow
    node_class = FlowNode
    block_class = FlowBlock


class FlowExecutor(ComponentExecutor[FlowExecutable, FlowBlock, FlowExecutionContext, Flow, FlowExecutionResult]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow
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
