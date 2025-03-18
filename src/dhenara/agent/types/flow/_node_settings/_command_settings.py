
from pydantic import Field

from dhenara.agent.types.data import RunEnvParams
from dhenara.ai.types.shared.base import BaseModel


class CommandSettings(BaseModel):
    """Settings for command execution nodes.

    Attributes:
        commands: List of commands to execute sequentially
        shell: Whether to use shell execution (enables pipe operations, etc.)
        working_dir: Working directory for command execution
        env_vars: Additional environment variables
        timeout: Maximum execution time in seconds (None for no timeout)
        fail_fast: If True, stop execution on first command failure
    """

    commands: list[str] = Field(
        ...,
        description="List of commands to execute sequentially",
        min_items=1,
    )
    shell: bool = Field(
        default=True,
        description="Whether to use shell execution (enables pipe operations, etc.)",
    )
    working_dir: str | None = Field(
        default=None,
        description="Working directory for command execution",
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables for command execution",
    )
    timeout: int | None = Field(default=60, description="Maximum execution time in seconds (None for no timeout)", ge=1)
    fail_fast: bool = Field(
        default=True,
        description="If True, stop execution on first command failure",
    )

    # @classmethod
    # @field_validaitor("commands")
    # def validate_commands(cls, v):
    #    """Validate that commands are non-empty strings"""
    #    if not all(isinstance(cmd, str) and cmd.strip() for cmd in v):
    #        raise ValueError("All commands must be non-empty strings")
    #    return v

    def get_formatted_commands_and_dir(self, run_env_params: RunEnvParams) -> tuple[list[str], str]:
        template_vars = run_env_params.get_template_variables()
        formatted_commands = []

        # Simple formatting using string's format method
        for command in self.commands:
            try:
                formatted_commands.append(command.format(**template_vars))
            except Exception as e:  # noqa: PERF203
                raise ValueError(f"get_formatted_commands: Error for command {command}: {e}")

        working_dir = self.get_working_dir(template_vars)
        return formatted_commands, working_dir

    def get_working_dir(
        self,
        template_vars: dict[str, str],
    ) -> str | None:
        """Resolve working directory with variable interpolation."""
        if not self.working_dir:
            raise ValueError("get_working_dir: working_dir is not set")

        try:
            formatted_dir = self.working_dir.format(**template_vars)
            return formatted_dir
        except Exception as e:
            raise ValueError(f"get_working_dir: Error for working_dir {self.working_dir}: {e}")
