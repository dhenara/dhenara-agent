
from pydantic import Field

from dhenara.agent.dsl.base import NodeInput

from .settings import FolderAnalyzerSettings


class FolderAnalyzerNodeInput(NodeInput):
    """Input for Folder Analyzer Node."""

    path: str | None = Field(None, description="Override path to analyze")
    exclude_patterns: list[str] | None = Field(None, description="Patterns to exclude (glob format)")
    settings_override: FolderAnalyzerSettings = None
