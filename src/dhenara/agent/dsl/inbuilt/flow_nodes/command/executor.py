import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

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
from dhenara.agent.dsl.flow import FlowNodeExecutor, FlowNodeTypeEnum
from dhenara.agent.observability.tracing import trace_node
from dhenara.agent.observability.tracing.data import TracingDataCategory, add_trace_attribute
from dhenara.ai.types.resource import ResourceConfig

from .input import CommandNodeInput
from .output import CommandNodeOutcome, CommandNodeOutputData, CommandResult
from .settings import CommandNodeSettings
from .tracing import command_node_tracing_profile

logger = logging.getLogger(__name__)


class CommandNodeExecutor(FlowNodeExecutor):
    input_model = CommandNodeInput
    setting_model = CommandNodeSettings
    _tracing_profile = command_node_tracing_profile

    def __init__(self):
        super().__init__(identifier="command_executor")

    @trace_node(FlowNodeTypeEnum.command.value)
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        node_input: NodeInput,
        resource_config: ResourceConfig,
    ) -> NodeExecutionResult[CommandNodeOutputData] | None:
        try:
            # Get settings from node definition or input override
            settings = node_definition.select_settings(node_input=node_input)
            if not isinstance(settings, CommandNodeSettings):
                raise ValueError(f"Invalid settings type: {type(settings)}")

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
                add_trace_attribute(
                    f"command_{formatted_commands.index(formatted_cmd)}",
                    formatted_cmd,
                    TracingDataCategory.primary,
                )

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

                    add_trace_attribute(
                        f"command_result_{formatted_commands.index(formatted_cmd)}",
                        {
                            "returncode": process.returncode,
                            "success": success,
                            "stdout_length": len(stdout) if stdout else 0,
                            "stderr_length": len(stderr) if stderr else 0,
                        },
                        TracingDataCategory.primary,
                    )
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

            add_trace_attribute(
                "commands_summary",
                {
                    "total": len(formatted_commands),
                    "successful": successful_commands,
                    "failed": failed_commands,
                    "all_succeeded": all_succeeded,
                },
                TracingDataCategory.primary,
            )

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

            return result

        except Exception as e:
            logger.exception(f"Command node execution error: {e}")
            return self.set_node_execution_failed(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
                message=f"Command execution failed: {e}",
            )

    def get_formatted_commands_and_dir(
        self,
        node_id: NodeID,
        execution_context: ExecutionContext,
        settings: CommandNodeSettings,
    ) -> tuple[list[str], Path]:
        """Format commands with variables and resolve working directory."""
        variables = {}

        # Format the commands with variables
        formatted_commands = []
        run_env_params = execution_context.run_context.run_env_params
        dad_dynamic_variables = execution_context.get_dad_dynamic_variables()

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
