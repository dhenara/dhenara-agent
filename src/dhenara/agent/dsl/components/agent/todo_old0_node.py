from pydantic import Field

from dhenara.agent.dsl.base import (
    Executable,
    ExecutableNode,
    ExecutableNodeDefinition,
    ExecutableTypeEnum,
    NodeExecutor,
)
from dhenara.agent.dsl.components.agent import AgentExecutionContext
from dhenara.agent.dsl.components.flow import FlowDefinition


class AgentExecutable(Executable):
    """Base class for all elements in a flow."""

    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.agent


class AgentNodeDefinition(ExecutableNodeDefinition[AgentExecutionContext]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent

    flow_def: FlowDefinition = Field(
        ...,
        description="Flow",
    )


class AgentNodeExecutor(NodeExecutor):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent


class AgentNode(ExecutableNode[AgentExecutable, AgentNodeDefinition, AgentExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.agent
