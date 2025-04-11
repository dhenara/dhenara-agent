
from pydantic import Field

from dhenara.agent.dsl.base import (
    ComponentTypeEnum,
    ExecutableBlock,
    ExecutableElement,
    ExecutableNode,
    ExecutableNodeDefinition,
    ExecutableReference,
    NodeExecutor,
)
from dhenara.agent.dsl.components.agent import AgentExecutionContext
from dhenara.agent.dsl.components.flow import Flow


class AgentElement(ExecutableElement):
    """Base class for all elements in a flow."""

    pass


class AgentNodeDefinition(ExecutableNodeDefinition[AgentExecutionContext]):
    component_type: ComponentTypeEnum = ComponentTypeEnum.agent

    flow: Flow = Field(
        ...,
        description="Flow",
    )


class AgentNodeExecutor(NodeExecutor):
    component_type: ComponentTypeEnum = ComponentTypeEnum.agent


class AgentNode(ExecutableNode[AgentElement, AgentNodeDefinition, AgentExecutionContext]):
    """A single execution node in the flow."""

    pass


class AgentBlock(ExecutableBlock[AgentElement, AgentExecutionContext]):
    pass


class AgentReference(ExecutableReference):
    """A reference to a value in the context."""

    pass
