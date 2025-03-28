# dhenara/agent/nodes/base.py


from pydantic import Field, model_validator

from dhenara.agent.dsl.flow import FlowNodeDefinition, FlowNodeTypeEnum

from .executor import FolderAnalyzerNodeExecutor
from .settings import FolderAnalyzerSettings


class FolderAnalyzerNode(FlowNodeDefinition):
    """Folder analyzer node."""

    node_type: str = FlowNodeTypeEnum.folder_analyzer
    settings: FolderAnalyzerSettings = Field(
        default=None,
        description="Folder analyzer settings",
    )

    def get_node_executor(self):
        return FolderAnalyzerNodeExecutor()

    @model_validator(mode="after")
    def validate_node_settings(self):
        if not self.settings:
            raise ValueError("settings is required for FolderAnalyzerNode")
        return self
