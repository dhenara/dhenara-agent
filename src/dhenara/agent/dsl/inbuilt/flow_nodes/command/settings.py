from pydantic import Field

from dhenara.agent.dsl.base import NodeSettings


class CommandNodeSettings(NodeSettings):
    """Configuration for command execution options."""

    commands: list[str] = Field(
        ...,
        description="Shell commands to execute",
    )
    working_dir: str | None = Field(
        default=None,
        description="Working directory for command execution",
    )
    env_vars: dict[str, str] | None = Field(
        default=None,
        description="Additional environment variables for command execution",
    )
    timeout: int = Field(
        default=60,
        description="Command execution timeout in seconds",
        ge=1,
    )
    shell: bool = Field(
        default=True,
        description="Whether to use shell for execution",
    )
    fail_fast: bool = Field(
        default=True,
        description="Whether to stop execution if a command fails",
    )
