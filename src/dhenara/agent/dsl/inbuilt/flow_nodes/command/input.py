from pydantic import Field

from dhenara.agent.dsl.base import NodeInput

from .settings import CommandNodeSettings


class CommandNodeInput(NodeInput):
    """Input for the Command Node."""

    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables for command execution",
    )
    commands: list[str] = Field(
        default_factory=list,
        description="Override the list of commands to execute",
    )
    settings_override: CommandNodeSettings | None = None
