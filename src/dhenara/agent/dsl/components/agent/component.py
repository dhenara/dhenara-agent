from typing import Any

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentExecutor,
    ExecutableTypeEnum,
)
from dhenara.agent.dsl.components.agent import (
    AgentBlock,
    AgentExecutable,
    AgentExecutionContext,
    AgentNode,
)
from dhenara.agent.observability.tracing.decorators.fns2 import trace_method


class AgentExecutionResult(ComponentExecutionResult):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent


class Agent(ComponentDefinition[AgentExecutable, AgentNode, AgentBlock, AgentExecutionContext]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent
    node_class = AgentNode
    block_class = AgentBlock


class AgentExecutor(
    ComponentExecutor[
        AgentExecutable,
        AgentBlock,
        AgentExecutionContext,
        Agent,
        AgentExecutionResult,
    ]
):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent
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
