# dhenara/agent/dsl/inbuilt/flow_nodes/file_operation/input.py

from pydantic import Field

from dhenara.agent.dsl.base import NodeInput

from .settings import FileOperationNodeSettings


class FileOperationNodeInput(NodeInput):
    """Input for the File Operation Node."""

    settings_override: FileOperationNodeSettings | None = Field(
        None,
        description="Override the node settings",
    )
