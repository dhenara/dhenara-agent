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
    NodeID,
    NodeInput,
    NodeOutput,
)
from dhenara.agent.dsl.components.flow import FlowNodeExecutionResult, FlowNodeExecutor
from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.observability.tracing import trace_node
from dhenara.agent.observability.tracing.data import add_trace_attribute

from .input import CommandNodeInput
from .output import CommandNodeOutcome, CommandNodeOutput, CommandNodeOutputData, CommandResult
from .settings import CommandNodeSettings
from .tracing import command_node_tracing_profile, commands_data_attr, commands_summary_attr

logger = logging.getLogger(__name__)


class CommandNodeExecutionResult(FlowNodeExecutionResult[CommandNodeInput, CommandNodeOutput, CommandNodeOutcome]):
    pass


class CommandNodeExecutor(FlowNodeExecutor):
    node_type = FlowNodeTypeEnum.command.value
    input_model = CommandNodeInput
    setting_model = CommandNodeSettings
    _tracing_profile = command_node_tracing_profile

    def get_result_class(self):
        return CommandNodeExecutionResult

    @trace_node(FlowNodeTypeEnum.command.value)
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
    ) -> CommandNodeExecutionResult | None:
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
            command_results_trace_data = []

            for formatted_cmd in formatted_commands:
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

                    command_results_trace_data.append(
                        {
                            "index": formatted_commands.index(formatted_cmd),
                            "command": formatted_cmd,
                            "success": success,
                            "returncode": process.returncode,
                            "stdout_length": len(stdout) if stdout else 0,
                            "stderr_length": len(stderr) if stderr else 0,
                        },
                    )
                    # Handle fail_fast
                    if settings.fail_fast and not success:
                        logger.error(f"Command failed, stopping execution: {formatted_cmd}")
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

            add_trace_attribute(commands_data_attr, command_results_trace_data)
            add_trace_attribute(
                commands_summary_attr,
                {
                    "total": len(formatted_commands),
                    "successful": successful_commands,
                    "failed": failed_commands,
                    "all_succeeded": all_succeeded,
                },
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
            result = CommandNodeExecutionResult(
                node_identifier=node_id,
                execution_status=ExecutionStatusEnum.COMPLETED if all_succeeded else ExecutionStatusEnum.FAILED,
                input=node_input,
                output=node_output,
                outcome=outcome,
                created_at=datetime.now(),
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

        for cmd in settings.commands:
            cmd = DADTemplateEngine.render_dad_template(
                template=cmd,
                variables=variables,
                execution_context=execution_context,
            )
            formatted_commands.append(cmd)

        # Resolve working directory
        working_dir = settings.working_dir or str(run_env_params.run_dir)
        working_dir = DADTemplateEngine.render_dad_template(
            template=working_dir,
            variables=variables,
            execution_context=execution_context,
        )

        return formatted_commands, Path(working_dir).expanduser().resolve()
