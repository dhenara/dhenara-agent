from typing import Any

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentExecutor,
    ExecutableComponent,
    ExecutableTypeEnum,
)
from dhenara.agent.dsl.components.agent import (
    AgentExecutable,
    AgentExecutionContext,
    AgentNode,
)
from dhenara.agent.dsl.components.flow.component import Flow, FlowDefinition
from dhenara.agent.observability.tracing.decorators.fns2 import trace_method


class AgentExecutionResult(ComponentExecutionResult):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent


class AgentDefinition(ComponentDefinition[AgentExecutable, AgentNode, AgentExecutionContext]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent
    node_class = AgentNode

    def subagent(
        self,
        id: str,  # noqa: A002
        definition: "AgentDefinition",
    ) -> "ComponentDefinition":
        """Add a component to the flow."""

        if not isinstance(definition, type(self)):
            raise ValueError(f"Unsupported type for body: {type(definition)}. Expected {type(self)}")

        self.elements.append(Flow(id=id, definition=definition))
        return self

    def subflow(
        self,
        id: str,  # noqa: A002
        definition: FlowDefinition,
    ) -> "ComponentDefinition":
        """Add a component to the flow."""

        if not isinstance(definition, type(self)):
            raise ValueError(f"Unsupported type for body: {type(definition)}. Expected {type(self)}")

        self.elements.append(Agent(id=id, definition=definition))
        return self


class AgentExecutor(
    ComponentExecutor[
        AgentExecutable,
        AgentExecutionContext,
        AgentDefinition,
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


# ExecutableAgent
class Agent(ExecutableComponent[AgentExecutable, AgentDefinition, AgentExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow
