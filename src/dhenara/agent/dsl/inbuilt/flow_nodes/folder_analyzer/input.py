from dhenara.agent.dsl.base import NodeInput

from .settings import FolderAnalyzerSettings


class FolderAnalyzerNodeInput(NodeInput):
    """Input for Folder Analyzer Node."""

    settings_override: FolderAnalyzerSettings = None
