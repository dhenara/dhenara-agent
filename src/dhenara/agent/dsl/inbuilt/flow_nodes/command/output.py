from typing import Any

from pydantic import Field

from dhenara.agent.dsl.base import NodeOutcome, NodeOutput
from dhenara.agent.types.base import BaseModel


class CommandResult(BaseModel):
    """Result of a single command execution."""

    command: str
    returncode: int
    stdout: str
    stderr: str
    success: bool
    error: str | None = None


class CommandNodeOutputData(BaseModel):
    """Output data for the Command Node."""

    all_succeeded: bool
    results: list[CommandResult]


class CommandNodeOutput(NodeOutput[CommandNodeOutputData]):
    pass


class CommandNodeOutcome(NodeOutcome):
    """Outcome for the Command Node."""

    all_succeeded: bool = Field(default=False)
    commands_executed: int = Field(default=0)
    successful_commands: int = Field(default=0)
    failed_commands: int = Field(default=0)
    results: list[dict[str, Any]] = Field(default_factory=list)
