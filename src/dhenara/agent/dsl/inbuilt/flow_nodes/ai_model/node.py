# dhenara/agent/nodes/base.py

from pydantic import Field, field_validator, model_validator

from dhenara.agent.dsl.flow import FlowNodeDefinition, FlowNodeTypeEnum
from dhenara.ai.types import ResourceConfigItem

from .executor import AIModelNodeExecutor
from .settings import AIModelNodeSettings


class AIModelNode(FlowNodeDefinition):
    node_type: str = FlowNodeTypeEnum.ai_model_call

    settings: AIModelNodeSettings | None = Field(
        default=None,
        description="Node specific AP API settings/options",
    )
    resources: list[ResourceConfigItem] = Field(
        default_factory=list,
        description="List of resources to be used",
    )
    tools: list = Field(
        default_factory=list,
        description="Tools",
    )

    def get_node_executor(self):
        return AIModelNodeExecutor()

    @field_validator("resources")
    @classmethod
    def validate_node_resources(
        cls,
        v: list[ResourceConfigItem],
    ) -> list[ResourceConfigItem]:
        """Validate that node IDs are unique within the same flow level."""
        # Ignore empty lists
        if not v:
            return v

        default_count = sum(1 for resource in v if resource.is_default)
        if default_count > 1:
            raise ValueError("Only one resource can be set as default")

        # If there is only one resource, set it as default and return
        if len(v) == 1:
            v[0].is_default = True
            return v
        else:
            if default_count < 1:
                raise ValueError("resources: One resource should be set as default")
            return v

    @model_validator(mode="after")
    def validate_node_type_settings(self):
        if not (self.node_settings or self.input_settings):
            raise ValueError("node_settings or input_settings is required for AIModelCall")

        return self
