from pydantic import Field

from dhenara.agent.dsl.components.agent import AgentNodeDefinition
from dhenara.agent.dsl.inbuilt.agent_nodes.defs.enums import AgentNodeTypeEnum

from .executor import BasicAgentNodeExecutor
from .settings import BasicAgentNodeSettings


class BasicAgentNode(AgentNodeDefinition):
    """A basic agent that runs a single flow."""

    node_type: str = AgentNodeTypeEnum.ai_model_call

    settings: BasicAgentNodeSettings | None = Field(
        default=None,
        description="Node specific AP API settings/options",
    )

    def get_node_executor(self):
        return BasicAgentNodeExecutor()
