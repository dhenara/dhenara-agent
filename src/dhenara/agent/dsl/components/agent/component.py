from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutor,
)
from dhenara.agent.dsl.components.agent import (
    AgentBlock,
    AgentElement,
    AgentExecutionContext,
    AgentNode,
    AgentNodeDefinition,
)


class Agent(ComponentDefinition[AgentElement, AgentNode, AgentNodeDefinition, AgentExecutionContext]):
    node_class = AgentNode


class AgentExecutor(ComponentExecutor[AgentElement, AgentBlock, AgentExecutionContext, Agent]):
    block_class = AgentBlock
    context_class = AgentExecutionContext
    logger_path: str = "dhenara.dad.agent"
