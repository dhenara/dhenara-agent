from pydantic import Field, model_validator

from dhenara.agent.dsl.components.flow import FlowNodeDefinition
from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum

from .executor import CommandNodeExecutor
from .settings import CommandNodeSettings


class CommandNode(FlowNodeDefinition):
    """Command execution node."""

    node_type: str = FlowNodeTypeEnum.command.value
    settings: CommandNodeSettings = Field(
        default=None,
        description="Command execution settings",
    )

    def get_executor_class(self):
        return CommandNodeExecutor

    @model_validator(mode="after")
    def validate_node_settings(self):
        if not self.settings:
            raise ValueError("settings is required for CommandNode")
        return self
