from pydantic import Field, model_validator

from dhenara.agent.dsl.flow import FlowNodeDefinition, FlowNodeTypeEnum

from .executor import FileOperationNodeExecutor
from .settings import FileOperationNodeSettings


class FileOperationNode(FlowNodeDefinition):
    """File operation node."""

    node_type: str = FlowNodeTypeEnum.file_operation
    settings: FileOperationNodeSettings = Field(
        default=None,
        description="File operation settings",
    )

    def get_node_executor(self):
        return FileOperationNodeExecutor()

    @model_validator(mode="after")
    def validate_node_settings(self):
        if not self.settings and not self.pre_execute_input_required:
            raise ValueError("settings is required for FileOperationNode when not requiring input")
        return self
