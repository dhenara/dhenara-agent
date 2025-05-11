from pydantic import Field, model_validator

from dhenara.agent.dsl.components.flow import FlowNodeDefinition
from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum

from .executor import FolderAnalyzerNodeExecutor
from .settings import FolderAnalyzerSettings


class FolderAnalyzerNode(FlowNodeDefinition):
    """Folder analyzer node."""

    node_type: str = FlowNodeTypeEnum.folder_analyzer.value
    settings: FolderAnalyzerSettings | None = Field(
        default=None,
        description="Folder analyzer settings. Must be provided either in definition or via inputs",
    )

    def get_executor_class(self):
        return FolderAnalyzerNodeExecutor

    @model_validator(mode="after")
    def validate_node_settings(self):
        if not self.settings and not self.trigger_pre_execute_input_required:
            raise ValueError("settings is required for FolderAnalyzerNode when not requiring input")
        return self
