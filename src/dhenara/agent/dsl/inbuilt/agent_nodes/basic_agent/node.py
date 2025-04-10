from pydantic import Field

from dhenara.agent.dsl.components.agent import AgentNodeDefinition
from dhenara.agent.dsl.inbuilt.agent_nodes.defs import AgentNodeTypeEnum

from .executor import BasicAgentNodeExecutor
from .settings import BasicAgentNodeSettings


class BasicAgentNode(AgentNodeDefinition):
    """A basic agent that runs a single flow."""

    node_type: str = AgentNodeTypeEnum.basic_agent.value

    settings: BasicAgentNodeSettings | None = Field(
        default=None,
        description="Node specific AP API settings/options",
    )

    def get_executor_class(self):
        return BasicAgentNodeExecutor
