from pydantic import Field

from dhenara.agent.dsl.components.flow import FlowNodeDefinition
from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum

from .executor import AIModelNodeExecutor
from .settings import AIModelNodeSettings


class AIModelNode(FlowNodeDefinition):
    node_type: str = FlowNodeTypeEnum.ai_model_call

    settings: AIModelNodeSettings | None = Field(
        default=None,
        description="Node specific AP API settings/options",
    )

    def get_executor_class(self):
        return AIModelNodeExecutor
