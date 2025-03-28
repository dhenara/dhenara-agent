from pathlib import Path

from pydantic import Field

from dhenara.agent.dsl.base import NodeSettings
from dhenara.agent.types.data import RunEnvParams


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

    def get_formatted_commands_and_dir(self, run_env_params: RunEnvParams) -> tuple[list[str], Path]:
        """Format commands with variables and resolve working directory."""
        variables = run_env_params.get_template_variables()

        # Format the commands with variables
        formatted_commands = []
        for cmd in self.commands:
            for var_name, var_value in variables.items():
                cmd = cmd.replace(f"{{{var_name}}}", str(var_value))
            formatted_commands.append(cmd)

        # Resolve working directory
        working_dir = self.working_dir or str(run_env_params.run_dir)
        for var_name, var_value in variables.items():
            working_dir = working_dir.replace(f"{{{var_name}}}", str(var_value))

        return formatted_commands, Path(working_dir).expanduser().resolve()
