from typing import Any

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentExecutor,
    ComponentTypeEnum,
)
from dhenara.agent.dsl.components.agent import (
    AgentBlock,
    AgentElement,
    AgentExecutionContext,
    AgentNode,
    AgentNodeDefinition,
)
from dhenara.agent.observability.tracing.decorators.fns2 import trace_method


class AgentExecutionResult(ComponentExecutionResult):
    component_type: ComponentTypeEnum = ComponentTypeEnum.agent


class Agent(ComponentDefinition[AgentElement, AgentNode, AgentNodeDefinition, AgentExecutionContext]):
    component_type: ComponentTypeEnum = ComponentTypeEnum.agent
    node_class = AgentNode


class AgentExecutor(
    ComponentExecutor[
        AgentElement,
        AgentBlock,
        AgentExecutionContext,
        Agent,
        AgentExecutionResult,
    ]
):
    component_type: ComponentTypeEnum = ComponentTypeEnum.agent
    block_class = AgentBlock
    context_class = AgentExecutionContext
    result_class = AgentExecutionResult
    logger_path: str = "dhenara.dad.agent"

    # Deinfe abstractmethod with proper trace name
    @trace_method("execute_agent")
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
