from pydantic import Field, model_validator

from dhenara.agent.dsl.components.flow import FlowNodeDefinition
from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum

from .executor import FileOperationNodeExecutor
from .settings import FileOperationNodeSettings


class FileOperationNode(FlowNodeDefinition):
    """File operation node."""

    node_type: str = FlowNodeTypeEnum.file_operation.value
    settings: FileOperationNodeSettings | None = Field(
        default=None,
        description="File operation settings. Must be provided either in definition or via inputs",
    )

    def get_executor_class(self):
        return FileOperationNodeExecutor

    @model_validator(mode="after")
    def validate_node_settings(self):
        if not self.settings and not self.trigger_pre_execute_input_required:
            raise ValueError("settings is required for FileOperationNode when not requiring input")
        return self
