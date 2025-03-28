import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dhenara.agent.dsl.base import (
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

from .input import FileOperationNodeInput
from .output import FileOperationNodeOutcome, FileOperationNodeOutputData, OperationResult
from .settings import FileOperation, FileOperationNodeSettings

logger = logging.getLogger(__name__)


class FileOperationNodeExecutor(FlowNodeExecutor):
    """Executor for File Operation Node."""

    input_model = FileOperationNodeInput
    setting_model = FileOperationNodeSettings

    def __init__(self):
        super().__init__(identifier="file_operation_executor")

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

            # Extract file operations from input or settings
            base_directory = "."
            operations = []

            if hasattr(node_input, "base_directory") and node_input.base_directory:
                base_directory = node_input.base_directory
            elif hasattr(settings, "base_directory") and settings.base_directory:
                base_directory = settings.base_directory

            # Resolve base directory with variables
            variables = execution_context.run_env_params.get_template_variables()
            for var_name, var_value in variables.items():
                base_directory = base_directory.replace(f"{{{var_name}}}", str(var_value))

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
            results = []
            successful_operations = 0
            failed_operations = 0
            errors = []

            for operation in operations:
                try:
                    full_path = Path(base_directory) / operation.path

                    if operation.type == "create_directory":
                        full_path.mkdir(parents=True, exist_ok=True)
                        results.append(OperationResult(type="create_directory", path=operation.path, success=True))
                        successful_operations += 1

                    elif operation.type == "create_file":
                        content = operation.content or ""
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(full_path, "w") as f:  # noqa: ASYNC230
                            f.write(content)
                        results.append(OperationResult(type="create_file", path=operation.path, success=True))
                        successful_operations += 1

                    elif operation.type == "modify_file":
                        if not full_path.exists():
                            error_msg = f"File does not exist: {operation.path}"
                            results.append(
                                OperationResult(type="modify_file", path=operation.path, success=False, error=error_msg)
                            )
                            errors.append(error_msg)
                            failed_operations += 1
                            continue

                        content = operation.content or ""
                        with open(full_path, "w") as f:  # noqa: ASYNC230
                            f.write(content)
                        results.append(OperationResult(type="modify_file", path=operation.path, success=True))
                        successful_operations += 1

                    elif operation.type == "delete":
                        if full_path.is_file():
                            os.remove(full_path)
                        elif full_path.is_dir():
                            import shutil

                            shutil.rmtree(full_path)
                        results.append(OperationResult(type="delete", path=operation.path, success=True))
                        successful_operations += 1

                    else:
                        error_msg = f"Unknown operation type: {operation.type}"
                        results.append(
                            OperationResult(type=operation.type, path=operation.path, success=False, error=error_msg)
                        )
                        errors.append(error_msg)
                        failed_operations += 1

                except Exception as e:
                    error_msg = f"Error performing operation {operation.type} on {operation.path}: {e}"
                    results.append(
                        OperationResult(type=operation.type, path=operation.path, success=False, error=error_msg)
                    )
                    errors.append(error_msg)
                    failed_operations += 1

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

            # Create node output
            node_output = NodeOutput[FileOperationNodeOutputData](data=output_data)

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
            logger.exception(f"File operation execution error: {e}")
            self.set_node_execution_failed(
                node_definition=node_definition,
                execution_context=execution_context,
                message=f"File operation failed: {e}",
            )
            return None
