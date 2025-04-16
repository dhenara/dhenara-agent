from typing import ClassVar

from pydantic import Field

from dhenara.agent.dsl.base import (
    Executable,
    ExecutableBlock,
    ExecutableNode,
    ExecutableNodeDefinition,
    ExecutableReference,
    ExecutableTypeEnum,
    NodeExecutor,
)
from dhenara.agent.dsl.components.agent import AgentExecutionContext
from dhenara.agent.dsl.components.flow import Flow


class AgentExecutable(Executable):
    """Base class for all elements in a flow."""

    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.agent


class AgentNodeDefinition(ExecutableNodeDefinition[AgentExecutionContext]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent

    flow: Flow = Field(
        ...,
        description="Flow",
    )


class AgentNodeExecutor(NodeExecutor):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent


class AgentNode(ExecutableNode[AgentExecutable, AgentNodeDefinition, AgentExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.agent


class AgentBlock(ExecutableBlock[AgentExecutable, AgentNode, AgentExecutionContext]):
    node_class: ClassVar[type[AgentNode]] = AgentNode

    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.agent


class AgentReference(ExecutableReference):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.agent
