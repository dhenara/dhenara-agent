# ruff: noqa: ASYNC230 : TODO_FUTURE
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dhenara.agent.dsl.base import (
    ExecutableNodeDefinition,
    ExecutionContext,
    ExecutionStatusEnum,
    NodeExecutionResult,
    NodeID,
    NodeInput,
    NodeOutput,
)
from dhenara.agent.dsl.base.data.dad_template_engine import DADTemplateEngine
from dhenara.agent.dsl.flow import FlowNodeExecutor, FlowNodeTypeEnum
from dhenara.agent.dsl.inbuilt.flow_nodes.file_operation.types import (
    FileModificationContent,
    FileOperation,
    FileOperationType,
)
from dhenara.agent.observability.tracing import trace_node
from dhenara.agent.observability.tracing.data import TracingDataCategory, add_trace_attribute
from dhenara.ai.types.resource import ResourceConfig

from .input import FileOperationNodeInput
from .output import FileOperationNodeOutcome, FileOperationNodeOutputData, OperationResult
from .settings import FileOperationNodeSettings
from .tracing import file_operation_node_tracing_profile

logger = logging.getLogger(__name__)


class FileOperationNodeExecutor(FlowNodeExecutor):
    """Executor for file system operations including creation, modification, and deletion of files and directories."""

    input_model = FileOperationNodeInput
    setting_model = FileOperationNodeSettings
    _tracing_profile = file_operation_node_tracing_profile

    def __init__(self):
        super().__init__(identifier="file_operation_executor")

    @trace_node(FlowNodeTypeEnum.file_operation.value)
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        node_input: NodeInput,
        resource_config: ResourceConfig,
    ) -> NodeExecutionResult[FileOperationNodeOutputData] | None:
        try:
            # Get settings from node definition or input override
            settings = node_definition.select_settings(node_input=node_input)

            # Override path if provided in input
            base_directory = self.get_formatted_base_directory(
                node_input=node_input,
                execution_context=execution_context,
                settings=settings,
            )
            add_trace_attribute("base_directory", str(base_directory), TracingDataCategory.primary)

            operations: list[FileOperation] = []

            # Extract operations from operations_template if provided
            if hasattr(settings, "operations_template") and settings.operations_template is not None:
                template_result = DADTemplateEngine.render_dad_template(
                    template=settings.operations_template,
                    variables={},
                    dad_dynamic_variables=execution_context.get_dad_dynamic_variables(),
                    run_env_params=execution_context.run_context.run_env_params,
                    node_execution_results=execution_context.execution_results,
                    mode="expression",
                )

                # Parse operations from template result (which could be a JSON string)
                if template_result:
                    try:
                        # Try to parse as JSON first
                        parsed_ops = json.loads(template_result)
                        if isinstance(parsed_ops, list):
                            operations = [FileOperation(**op) if isinstance(op, dict) else op for op in parsed_ops]
                        elif isinstance(parsed_ops, dict) and "operations" in parsed_ops:
                            operations = [
                                FileOperation(**op) if isinstance(op, dict) else op for op in parsed_ops["operations"]
                            ]
                    except json.JSONDecodeError:
                        # If not valid JSON, log an error
                        logger.error(f"Unable to parse operations from template result: {template_result}")

            # If no operations from template, try other sources
            if not operations:
                # Get operations from different possible sources
                if hasattr(node_input, "json_operations") and node_input.json_operations:
                    # Parse JSON operations
                    try:
                        ops_data = json.loads(node_input.json_operations)
                        if isinstance(ops_data, dict) and "operations" in ops_data:
                            operations = [FileOperation(**op) for op in ops_data["operations"]]
                        elif isinstance(ops_data, list):
                            operations = [FileOperation(**op) for op in ops_data]
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON in operations: {e}")
                elif hasattr(node_input, "operations") and node_input.operations:
                    operations = node_input.operations
                elif hasattr(settings, "operations") and settings.operations:
                    operations = settings.operations

            if not operations:
                raise ValueError("No file operations specified")

            # Execute operations
            results: list[OperationResult] = []
            successful_operations = 0
            failed_operations = 0
            errors: list[str] = []

            add_trace_attribute("operations_count", len(operations), TracingDataCategory.primary)

            for operation in operations:
                add_trace_attribute(
                    f"operation_{operations.index(operation)}",
                    {
                        "type": operation.type,
                        "path": operation.path,
                    },
                    TracingDataCategory.primary,
                )

                try:
                    # Validate the operation
                    if not operation.validate_content_type():
                        error_msg = f"Invalid content type for operation {operation.type} on {operation.path}"
                        results.append(
                            OperationResult(type=operation.type, path=operation.path, success=False, error=error_msg)
                        )
                        errors.append(error_msg)
                        failed_operations += 1
                        continue

                    full_path = Path(base_directory) / operation.path

                    if operation.type == FileOperationType.create_directory.value:
                        full_path.mkdir(parents=True, exist_ok=True)
                        results.append(OperationResult(type="create_directory", path=operation.path, success=True))
                        successful_operations += 1

                    elif operation.type == FileOperationType.create_file.value:
                        # Content should be a string for create_file
                        content = operation.content or ""
                        if not isinstance(content, str):
                            error_msg = f"Expected string content for create_file operation on {operation.path}"
                            results.append(
                                OperationResult(type="create_file", path=operation.path, success=False, error=error_msg)
                            )
                            errors.append(error_msg)
                            failed_operations += 1
                            continue

                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(full_path, "w") as f:
                            f.write(content)
                        results.append(OperationResult(type="create_file", path=operation.path, success=True))
                        successful_operations += 1

                    elif operation.type == FileOperationType.modify_file.value:
                        if not full_path.exists():
                            error_msg = f"File does not exist: {operation.path}"
                            results.append(
                                OperationResult(type="modify_file", path=operation.path, success=False, error=error_msg)
                            )
                            errors.append(error_msg)
                            failed_operations += 1
                            continue

                        # Content should be FileModificationContent for modify_file
                        mod_content = operation.content
                        if not isinstance(mod_content, FileModificationContent):
                            error_msg = (
                                f"Expected FileModificationContent for modify_file operation on {operation.path}"
                            )
                            results.append(
                                OperationResult(type="modify_file", path=operation.path, success=False, error=error_msg)
                            )
                            errors.append(error_msg)
                            failed_operations += 1
                            continue

                        # Read the file content
                        with open(full_path) as f:
                            file_content = f.read()

                        # Find the start and end points
                        start_idx = file_content.find(mod_content.start_point_match)
                        end_idx = file_content.find(
                            mod_content.end_point_match, start_idx + len(mod_content.start_point_match)
                        )

                        if start_idx == -1 or end_idx == -1:
                            error_msg = f"Could not find modification points in {operation.path}"
                            results.append(
                                OperationResult(type="modify_file", path=operation.path, success=False, error=error_msg)
                            )
                            errors.append(error_msg)
                            failed_operations += 1
                            continue

                        # Perform the modification
                        new_content = (
                            file_content[: start_idx + len(mod_content.start_point_match)]
                            + mod_content.new_content
                            + file_content[end_idx:]
                        )

                        # Write the modified content
                        with open(full_path, "w") as f:
                            f.write(new_content)

                        results.append(OperationResult(type="modify_file", path=operation.path, success=True))
                        successful_operations += 1

                    elif operation.type in [
                        FileOperationType.delete_directory.value,
                        FileOperationType.delete_file.value,
                    ]:
                        if not full_path.exists():
                            error_msg = f"Path does not exist: {operation.path}"
                            results.append(
                                OperationResult(
                                    type=operation.type, path=operation.path, success=False, error=error_msg
                                )
                            )
                            errors.append(error_msg)
                            failed_operations += 1
                            continue

                        if full_path.is_file():
                            os.remove(full_path)
                        elif full_path.is_dir():
                            import shutil

                            shutil.rmtree(full_path)
                        results.append(OperationResult(type=operation.type, path=operation.path, success=True))
                        successful_operations += 1

                    else:
                        error_msg = f"Unknown operation type: {operation.type}"
                        results.append(
                            OperationResult(type=operation.type, path=operation.path, success=False, error=error_msg)
                        )
                        errors.append(error_msg)
                        failed_operations += 1

                except Exception as e:
                    error_msg = f"Error performing operation {operation.type} on {operation.path}: {e!s}"
                    results.append(
                        OperationResult(type=operation.type, path=operation.path, success=False, error=error_msg)
                    )
                    errors.append(error_msg)
                    failed_operations += 1
                    logger.error(error_msg, exc_info=True)

                op_idx = operations.index(operation)
                if op_idx < len(results):
                    result = results[op_idx]
                    add_trace_attribute(
                        f"operation_result_{op_idx}",
                        {
                            "type": result.type,
                            "path": result.path,
                            "success": result.success,
                            "error": result.error,
                        },
                        TracingDataCategory.primary,
                    )

            # Create output data
            all_succeeded = failed_operations == 0
            output_data = FileOperationNodeOutputData(
                success=all_succeeded, operations_count=len(operations), results=results
            )

            # Create outcome
            outcome = FileOperationNodeOutcome(
                success=all_succeeded,
                operations_count=len(operations),
                successful_operations=successful_operations,
                failed_operations=failed_operations,
                errors=errors,
            )

            add_trace_attribute(
                "operations_summary",
                {
                    "total": len(operations),
                    "successful": successful_operations,
                    "failed": failed_operations,
                    "all_succeeded": all_succeeded,
                },
                TracingDataCategory.primary,
            )

            # Create node output
            node_output = NodeOutput[FileOperationNodeOutputData](data=output_data)

            # Create execution result
            result = NodeExecutionResult[FileOperationNodeOutputData](
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
            logger.exception(f"File operation execution error: {e!s}")
            return self.set_node_execution_failed(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
                message=f"File operation failed: {e!s}",
            )

    def get_formatted_base_directory(
        self,
        node_input: FileOperationNodeInput,
        execution_context: ExecutionContext,
        settings: FileOperationNodeSettings,
    ) -> str:
        """Format path with variables."""
        variables = {}
        dad_dynamic_variables = execution_context.get_dad_dynamic_variables()
        # Extract file operations from input or settings
        base_directory = "."
        # Determine base directory from input or settings
        if hasattr(node_input, "base_directory") and node_input.base_directory:
            base_directory = node_input.base_directory
        elif hasattr(settings, "base_directory") and settings.base_directory:
            base_directory = settings.base_directory
        # Resolve base directory with variables
        return DADTemplateEngine.render_dad_template(
            template=base_directory,
            variables=variables,
            dad_dynamic_variables=dad_dynamic_variables,
            run_env_params=execution_context.run_context.run_env_params,
            node_execution_results=None,
            mode="standard",
        )
