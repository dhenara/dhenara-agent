# dhenara/agent/engine/handlers/command.py
import asyncio
import logging
import os
from typing import Any

from dhenara.agent.dsl.base import ExecutableNodeDefinition, ExecutionContext, NodeInput
from dhenara.agent.engine.handler import NodeHandler
from dhenara.agent.types.flow import CommandSettings
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)


class CommandHandler(NodeHandler):
    """Handler for executing shell commands."""

    def __init__(self):
        super().__init__(identifier="command_handler")

    async def handle(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        resource_config: ResourceConfig,
    ) -> Any:
        """Execute commands defined in the flow node."""
        try:
            # Validate command settings
            if not hasattr(node_definition, "command_settings"):
                raise ValueError("command_settings is required for command nodes")

            # If command_settings is a dict, convert it to a CommandSettings object
            if isinstance(node_definition.command_settings, dict):
                command_settings = CommandSettings(**node_definition.command_settings)
            else:
                command_settings = node_definition.command_settings

            # Set up execution environment
            env = os.environ.copy()
            if command_settings.env_vars:
                env.update(command_settings.env_vars)

            # Execute commands sequentially
            results = []
            formatted_commands, working_dir = command_settings.get_formatted_commands_and_dir(
                run_env_params=execution_context.run_env_params
            )

            for formatted_cmd in formatted_commands:
                # Interpolate variables in command
                logger.debug(f"Executing command: {formatted_cmd}")

                # Execute the command
                process = await asyncio.create_subprocess_shell(
                    formatted_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=command_settings.shell,
                    cwd=working_dir,
                    env=env,
                )

                try:
                    # Wait for command to complete with optional timeout
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=command_settings.timeout)

                    # Process result
                    result = {
                        "command": formatted_cmd,
                        "returncode": process.returncode,
                        "stdout": stdout.decode() if stdout else "",
                        "stderr": stderr.decode() if stderr else "",
                        "success": process.returncode == 0,
                    }
                    results.append(result)

                    # Handle fail_fast
                    if command_settings.fail_fast and process.returncode != 0:
                        logger.warning(f"Command failed, stopping execution: {formatted_cmd}")
                        break

                except asyncio.TimeoutError:
                    await process.kill()
                    results.append(
                        {
                            "command": formatted_cmd,
                            "returncode": None,
                            "stdout": "",
                            "stderr": "Command execution timed out",
                            "success": False,
                            "error": "timeout",
                        }
                    )
                    if command_settings.fail_fast:
                        break

            return {
                "all_succeeded": all(r["success"] for r in results),
                "results": results,
            }

        except Exception as e:
            logger.exception(f"Error executing command: {e}")
            raise DhenaraAPIError(f"Command execution failed: {e!s}")
