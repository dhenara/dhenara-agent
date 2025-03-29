import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dhenara.agent.dsl.base import (
    DADTemplateEngine,
    ExecutableNodeDefinition,
    ExecutionContext,
    ExecutionStatusEnum,
    NodeExecutionResult,
    NodeID,
    NodeInput,
    NodeOutput,
)
from dhenara.agent.dsl.flow import FlowNodeExecutor
from dhenara.ai.types.resource import ResourceConfig

from .input import CommandNodeInput
from .output import CommandNodeOutcome, CommandNodeOutputData, CommandResult
from .settings import CommandNodeSettings

logger = logging.getLogger(__name__)


class CommandNodeExecutor(FlowNodeExecutor):
    """Executor for Command Node."""

    input_model = CommandNodeInput
    setting_model = CommandNodeSettings

    def __init__(self):
        super().__init__(identifier="command_executor")

    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        node_input: NodeInput,
        resource_config: ResourceConfig,
    ) -> Any:
        try:
            # Get settings from node definition or input override
            settings = node_definition.select_settings(node_input=node_input)
            if not isinstance(settings, CommandNodeSettings):
                raise ValueError(f"Invalid settings type: {type(settings)}")

            # Override commands if provided in input
            commands = (
                node_input.commands if hasattr(node_input, "commands") and node_input.commands else settings.commands
            )

            # Set up execution environment
            env = os.environ.copy()
            if settings.env_vars:
                env.update(settings.env_vars)
            if hasattr(node_input, "env_vars") and node_input.env_vars:
                env.update(node_input.env_vars)

            # Get formatted commands and working directory
            formatted_commands, working_dir = self.get_formatted_commands_and_dir(
                node_id=node_id,
                execution_context=execution_context,
                settings=settings,
            )

            # Execute commands sequentially
            results = []
            all_succeeded = True
            successful_commands = 0
            failed_commands = 0

            for formatted_cmd in formatted_commands:
                logger.debug(f"Executing command: {formatted_cmd}")

                # Execute the command
                process = await asyncio.create_subprocess_shell(
                    formatted_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=settings.shell,
                    cwd=working_dir,
                    env=env,
                )

                try:
                    # Wait for command to complete with optional timeout
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=settings.timeout)

                    success = process.returncode == 0
                    if success:
                        successful_commands += 1
                    else:
                        failed_commands += 1
                        all_succeeded = False

                    # Process result
                    result = CommandResult(
                        command=formatted_cmd,
                        returncode=process.returncode,
                        stdout=stdout.decode() if stdout else "",
                        stderr=stderr.decode() if stderr else "",
                        success=success,
                    )
                    results.append(result)

                    # Handle fail_fast
                    if settings.fail_fast and not success:
                        logger.warning(f"Command failed, stopping execution: {formatted_cmd}")
                        break

                except asyncio.TimeoutError:
                    await process.kill()
                    failed_commands += 1
                    all_succeeded = False

                    results.append(
                        CommandResult(
                            command=formatted_cmd,
                            returncode=None,
                            stdout="",
                            stderr="Command execution timed out",
                            success=False,
                            error="timeout",
                        )
                    )
                    if settings.fail_fast:
                        break

            # Create output data
            output_data = CommandNodeOutputData(
                all_succeeded=all_succeeded,
                results=results,
            )

            # Create outcome data
            outcome = CommandNodeOutcome(
                all_succeeded=all_succeeded,
                commands_executed=len(results),
                successful_commands=successful_commands,
                failed_commands=failed_commands,
                results=[r.model_dump() for r in results],
            )

            # Create node output
            node_output = NodeOutput[CommandNodeOutputData](data=output_data)

            # Create execution result
            result = NodeExecutionResult(
                node_identifier=node_id,
                status=ExecutionStatusEnum.COMPLETED if all_succeeded else ExecutionStatusEnum.FAILED,
                input=node_input,
                output=node_output,
                outcome=outcome,
                created_at=datetime.now(),
            )

            # Update execution context
            self.update_execution_context(
                node_id=node_id,
                execution_context=execution_context,
                result=result,
            )

            return output_data

        except Exception as e:
            logger.exception(f"Command node execution error: {e}")
            self.set_node_execution_failed(
                node_definition=node_definition,
                execution_context=execution_context,
                message=f"Command execution failed: {e}",
            )
            return None

    def get_formatted_commands_and_dir(
        self,
        node_id: NodeID,
        execution_context: ExecutionContext,
        settings: CommandNodeSettings,
    ) -> tuple[list[str], Path]:
        """Format commands with variables and resolve working directory."""
        variables = {}
        dad_dynamic_variables = {
            "node_id": node_id,
        }

        # Format the commands with variables
        formatted_commands = []
        run_env_params = execution_context.run_context.run_env_params

        for cmd in settings.commands:
            cmd = DADTemplateEngine.render_dad_template(
                template=cmd,
                variables=variables,
                dad_dynamic_variables=dad_dynamic_variables,
                run_env_params=run_env_params,
                node_execution_results=None,
                mode="standard",
            )
            formatted_commands.append(cmd)

        # Resolve working directory
        working_dir = settings.working_dir or str(run_env_params.run_dir)
        working_dir = DADTemplateEngine.render_dad_template(
            template=working_dir,
            variables=variables,
            dad_dynamic_variables=dad_dynamic_variables,
            run_env_params=run_env_params,
            node_execution_results=None,
            mode="standard",
        )

        return formatted_commands, Path(working_dir).expanduser().resolve()
