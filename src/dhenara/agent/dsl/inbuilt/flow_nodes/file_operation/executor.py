import json
import logging
import os
import re
import shutil
from datetime import datetime
from difflib import unified_diff
from fnmatch import fnmatch
from pathlib import Path
from stat import filemode

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
from dhenara.agent.dsl.components.flow import FlowNodeExecutor
from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import EditOperation, FileMetadata, FileOperation
from dhenara.agent.observability.tracing import trace_node
from dhenara.agent.observability.tracing.data import TracingDataCategory, add_trace_attribute

from .input import FileOperationNodeInput
from .output import FileOperationNodeOutcome, FileOperationNodeOutput, FileOperationNodeOutputData, OperationResult
from .settings import FileOperationNodeSettings
from .tracing import file_operation_node_tracing_profile

logger = logging.getLogger(__name__)

FileOperationNodeExecutionResult = NodeExecutionResult[
    FileOperationNodeInput,
    FileOperationNodeOutput,
    FileOperationNodeOutcome,
]


class FileOperationNodeExecutor(FlowNodeExecutor):  # TODO: Use FileSytemOperationsMixin
    node_type = FlowNodeTypeEnum.file_operation.value
    input_model = FileOperationNodeInput
    setting_model = FileOperationNodeSettings
    _tracing_profile = file_operation_node_tracing_profile

    def get_result_class(self):
        return FileOperationNodeExecutionResult

    @trace_node(FlowNodeTypeEnum.file_operation.value)
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
    ) -> FileOperationNodeExecutionResult | None:
        try:
            # Get settings from node definition or input override
            settings = node_definition.select_settings(node_input=node_input)

            # Override base directory if provided in input
            base_directory = self.get_formatted_base_directory(
                node_input=node_input,
                settings=settings,
                execution_context=execution_context,
            )
            add_trace_attribute("base_directory", str(base_directory), TracingDataCategory.primary)

            # Get allowed directories
            allowed_directories = self._get_allowed_directories(node_input, settings)

            # Extract operations to perform
            operations = self._extract_operations(node_input, settings, execution_context)

            if not operations:
                raise ValueError("No file operations specified")

            # Validate all paths for security
            self._validate_paths(base_directory, operations, allowed_directories)

            # Execute operations
            results, successful_ops, failed_ops, errors = await self._execute_operations(
                base_directory, operations, settings
            )

            # Create output data
            all_succeeded = failed_ops == 0
            output_data = FileOperationNodeOutputData(
                base_directory=str(base_directory),
                success=all_succeeded,
                operations_count=len(operations),
                successful_operations=successful_ops,
                failed_operations=failed_ops,
                errors=errors,
            )

            # Create outcome
            outcome = FileOperationNodeOutcome(
                base_directory=str(base_directory),
                results=results,
            )

            add_trace_attribute(
                "operations_summary",
                {
                    "total": len(operations),
                    "successful": successful_ops,
                    "failed": failed_ops,
                    "all_succeeded": all_succeeded,
                },
                TracingDataCategory.primary,
            )

            # Create node output
            node_output = NodeOutput[FileOperationNodeOutputData](data=output_data)

            # Create execution result
            result = FileOperationNodeExecutionResult(
                node_identifier=node_id,
                status=ExecutionStatusEnum.COMPLETED if all_succeeded else ExecutionStatusEnum.FAILED,
                input=node_input,
                output=node_output,
                outcome=outcome,
                created_at=datetime.now(),
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
        settings: FileOperationNodeSettings,
        execution_context: ExecutionContext,
    ) -> str:
        """Format path with variables."""
        variables = {}
        dad_dynamic_variables = execution_context.get_dad_dynamic_variables()

        # Determine base directory from input or settings
        base_directory = "."
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
        )

    def _get_allowed_directories(
        self, node_input: FileOperationNodeInput, settings: FileOperationNodeSettings
    ) -> list[str]:
        """Get the list of allowed directories."""
        allowed_dirs = []

        # Check input first, then settings
        if hasattr(node_input, "allowed_directories") and node_input.allowed_directories:
            allowed_dirs = node_input.allowed_directories
        elif hasattr(settings, "allowed_directories") and settings.allowed_directories:
            allowed_dirs = settings.allowed_directories

        # If no directories specified, use the base directory
        if not allowed_dirs:
            return []

        # Normalize paths
        return [os.path.normpath(os.path.abspath(d)) for d in allowed_dirs]

    def _extract_operations(
        self,
        node_input: FileOperationNodeInput,
        settings: FileOperationNodeSettings,
        execution_context: ExecutionContext,
    ) -> list[FileOperation]:
        """Extract file operations from various sources."""
        operations: list[FileOperation] = []

        # Extract operations from operations_template if provided
        if settings.operations_template is not None:
            template_result = DADTemplateEngine.render_dad_template(
                template=settings.operations_template,
                variables={},
                dad_dynamic_variables=execution_context.get_dad_dynamic_variables(),
                run_env_params=execution_context.run_context.run_env_params,
                node_execution_results=execution_context.execution_results,
            )

            # Process operations based on the actual type returned
            if template_result:
                try:
                    # Handle list of operations
                    if isinstance(template_result, list):
                        operations = []
                        for op in template_result:
                            if isinstance(op, dict):
                                operations.append(FileOperation(**op))
                            elif isinstance(op, FileOperation):
                                operations.append(op)
                            else:
                                logger.warning(f"Unexpected operation type in list: {type(op)}")
                    # Handle single operation as dict
                    elif isinstance(template_result, dict):
                        operations = [FileOperation(**template_result)]
                    # Handle JSON string
                    elif isinstance(template_result, str):
                        try:
                            # Try parsing as JSON
                            parsed_ops = json.loads(template_result)
                            if isinstance(parsed_ops, list):
                                operations = [FileOperation(**op) for op in parsed_ops]
                            elif isinstance(parsed_ops, dict):
                                operations = [FileOperation(**parsed_ops)]
                            else:
                                logger.error(f"Unexpected structure in JSON string: {type(parsed_ops)}")
                        except json.JSONDecodeError:
                            logger.error(f"Unable to parse operations from template string: {template_result}")
                    # Handle other unexpected types
                    else:
                        logger.error(f"Unsupported template result type: {type(template_result)}")
                except Exception as e:
                    logger.error(f"Error processing operations from template: {e}", exc_info=True)

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

        return operations

    def _validate_paths(self, base_dir: str, operations: list[FileOperation], allowed_dirs: list[str]) -> None:
        """
        Validate paths for security concerns.
        Ensures all file operations are within allowed directories.
        """
        if not allowed_dirs:
            return  # No restrictions if no allowed directories specified

        base_path = Path(base_dir).resolve()

        for op in operations:
            # Check relevant paths based on operation type
            paths_to_check = []

            if op.path:
                paths_to_check.append(op.path)
            if op.paths:
                paths_to_check.extend(op.paths)
            if op.source:
                paths_to_check.append(op.source)
            if op.destination:
                paths_to_check.append(op.destination)

            for path_str in paths_to_check:
                # Get absolute path
                if os.path.isabs(path_str):
                    full_path = Path(path_str).resolve()
                else:
                    full_path = (base_path / path_str).resolve()

                # Check if path is within allowed directories
                path_allowed = False
                for allowed_dir in allowed_dirs:
                    allowed_path = Path(allowed_dir).resolve()
                    try:
                        # Check if path is within allowed directory
                        if str(full_path).startswith(str(allowed_path)):
                            path_allowed = True
                            break
                    except Exception:
                        # Skip invalid paths
                        continue

                if not path_allowed:
                    raise ValueError(f"Access denied - path outside allowed directories: {full_path}")

    async def _execute_operations(
        self,
        base_directory: str,
        operations: list[FileOperation],
        settings: FileOperationNodeSettings,
    ) -> tuple[list[OperationResult], int, int, list[str]]:
        """
        Execute all file operations and return results.

        Returns:
            tuple containing:
            - list of OperationResult objects
            - count of successful operations
            - count of failed operations
            - list of error messages
        """
        results: list[OperationResult] = []
        successful_operations = 0
        failed_operations = 0
        errors: list[str] = []

        add_trace_attribute("operations_count", len(operations), TracingDataCategory.primary)

        for i, operation in enumerate(operations):
            add_trace_attribute(
                f"operation_{i}",
                {
                    "type": operation.type,
                    "path": operation.path,
                },
                TracingDataCategory.primary,
            )

            try:
                # Validate the operation
                if not operation.validate_content_type():
                    error_msg = f"Invalid parameters for operation {operation.type}"
                    results.append(
                        OperationResult(type=operation.type, path=operation.path, success=False, error=error_msg)
                    )
                    errors.append(error_msg)
                    failed_operations += 1
                    if settings.fail_fast:
                        break
                    continue

                # Execute the operation based on type
                if operation.type == "read_file":
                    result = await self._read_file(base_directory, operation)
                elif operation.type == "read_multiple_files":
                    result = await self._read_multiple_files(base_directory, operation)
                elif operation.type == "create_file":
                    result = await self._write_file(base_directory, operation)
                elif operation.type == "edit_file":
                    result = await self._edit_file(base_directory, operation, settings)
                elif operation.type == "create_directory":
                    result = await self._create_directory(base_directory, operation)
                elif operation.type == "delete_directory":
                    result = await self._delete_directory(base_directory, operation)
                elif operation.type == "delete_file":
                    result = await self._delete_file(base_directory, operation)
                elif operation.type == "list_directory":
                    result = await self._list_directory(base_directory, operation)
                elif operation.type == "move_file":
                    result = await self._move_file(base_directory, operation)
                elif operation.type == "search_files":
                    result = await self._search_files(base_directory, operation)
                elif operation.type == "get_file_metadata":
                    result = await self._get_file_metadata(base_directory, operation)
                elif operation.type == "list_allowed_directories":
                    result = OperationResult(
                        type="list_allowed_directories",
                        success=True,
                        files=settings.allowed_directories if settings.allowed_directories else [],
                    )
                else:
                    error_msg = f"Unknown operation type: {operation.type}"
                    result = OperationResult(type=operation.type, path=operation.path, success=False, error=error_msg)

                results.append(result)

                if result.success:
                    successful_operations += 1
                else:
                    failed_operations += 1
                    if result.error:
                        errors.append(result.error)
                    if settings.fail_fast:
                        break

            except Exception as e:
                error_msg = f"Error performing operation {operation.type} on {operation.path}: {e!s}"
                results.append(
                    OperationResult(
                        type=operation.type,
                        path=operation.path,
                        success=False,
                        error=error_msg,
                    )
                )
                errors.append(error_msg)
                failed_operations += 1
                logger.error(error_msg, exc_info=True)
                if settings.fail_fast:
                    break

            # Add operation result to trace
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

        return results, successful_operations, failed_operations, errors

    async def _read_file(self, base_directory: str, operation: FileOperation) -> OperationResult:
        """Read contents of a file."""
        if not operation.path:
            return OperationResult(type="read_file", success=False, error="Path not specified")

        try:
            full_path = Path(base_directory) / operation.path
            if not full_path.exists():
                return OperationResult(
                    type="read_file", path=operation.path, success=False, error=f"File does not exist: {operation.path}"
                )

            if not full_path.is_file():
                return OperationResult(
                    type="read_file", path=operation.path, success=False, error=f"Path is not a file: {operation.path}"
                )

            content = full_path.read_text(encoding="utf-8")
            return OperationResult(type="read_file", path=operation.path, success=True, content=content)
        except Exception as e:
            return OperationResult(
                type="read_file", path=operation.path, success=False, error=f"Error reading file: {e}"
            )

    async def _read_multiple_files(self, base_directory: str, operation: FileOperation) -> OperationResult:
        """Read multiple files at once."""
        if not operation.paths:
            return OperationResult(type="read_multiple_files", success=False, error="No paths specified")

        try:
            results = []
            for file_path in operation.paths:
                try:
                    full_path = Path(base_directory) / file_path
                    if not full_path.exists():
                        results.append(f"{file_path}: Error - File does not exist")
                    elif not full_path.is_file():
                        results.append(f"{file_path}: Error - Path is not a file")
                    else:
                        content = full_path.read_text(encoding="utf-8")
                        results.append(f"{file_path}:\n{content}\n")
                except Exception as e:  # noqa: PERF203
                    results.append(f"{file_path}: Error - {e!s}")

            return OperationResult(type="read_multiple_files", success=True, content="\n---\n".join(results))
        except Exception as e:
            return OperationResult(type="read_multiple_files", success=False, error=f"Error reading files: {e}")

    async def _write_file(self, base_directory: str, operation: FileOperation) -> OperationResult:
        """Create a new file or overwrite existing file."""
        if not operation.path:
            return OperationResult(type="write_file", success=False, error="Path not specified")

        if not operation.content or not isinstance(operation.content, str):
            return OperationResult(
                type="write_file", path=operation.path, success=False, error="Content must be a string"
            )

        try:
            full_path = Path(base_directory) / operation.path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(operation.content, encoding="utf-8")
            return OperationResult(
                type="write_file" if operation.type == "write_file" else "create_file",
                path=operation.path,
                success=True,
            )
        except Exception as e:
            return OperationResult(
                type="write_file" if operation.type == "write_file" else "create_file",
                path=operation.path,
                success=False,
                error=f"Error writing file: {e}",
            )

    async def _edit_file(
        self, base_directory: str, operation: FileOperation, settings: FileOperationNodeSettings
    ) -> OperationResult:
        """Edit a file using the more advanced edit operations."""
        if not operation.path:
            return OperationResult(type="edit_file", success=False, error="Path not specified")

        if not operation.edits:
            return OperationResult(type="edit_file", path=operation.path, success=False, error="No edits specified")

        try:
            full_path = Path(base_directory) / operation.path
            if not full_path.exists():
                return OperationResult(
                    type="edit_file", path=operation.path, success=False, error=f"File does not exist: {operation.path}"
                )

            # Read the file content
            file_content = full_path.read_text(encoding="utf-8")

            # Normalize line endings
            file_content = self._normalize_line_endings(file_content)

            # Apply edits sequentially
            modified_content = file_content
            all_successful = True
            error_messages = []

            for edit in operation.edits:
                try:
                    # Apply a single edit
                    modified_content = self._apply_edit(modified_content, edit, settings.preserve_indentation)
                except Exception as e:  # noqa: PERF203
                    all_successful = False
                    error_messages.append(f"Failed to apply edit: {e!s}")
                    if settings.fail_fast:
                        break

            if not all_successful:
                return OperationResult(
                    type="edit_file", path=operation.path, success=False, error="\n".join(error_messages)
                )

            # Create diff if requested
            diff = None
            if settings.return_diff_format:
                diff = self._create_unified_diff(file_content, modified_content, operation.path)

            # Apply changes if not dry run
            if not operation.dry_run:
                full_path.write_text(modified_content, encoding="utf-8")

            return OperationResult(type="edit_file", path=operation.path, success=True, diff=diff)
        except Exception as e:
            return OperationResult(
                type="edit_file", path=operation.path, success=False, error=f"Error editing file: {e}"
            )

    def _apply_edit(self, content: str, edit: EditOperation, preserve_indentation: bool) -> str:
        """Apply a single edit operation to the content."""
        old_text = self._normalize_line_endings(edit.old_text)
        new_text = self._normalize_line_endings(edit.new_text)

        # If exact match exists, use it
        if old_text in content:
            # Check if we should preserve indentation
            if preserve_indentation and "\n" in old_text and "\n" in new_text:
                # Get the indentation of the first line of old_text in content
                idx = content.find(old_text)
                if idx > 0:
                    # Find the start of the line containing old_text
                    line_start = content.rfind("\n", 0, idx) + 1
                    indentation = content[line_start:idx]
                    if indentation.strip() == "":  # Only if it's whitespace
                        # Apply indentation to all lines of new_text except the first
                        lines = new_text.split("\n")
                        for i in range(1, len(lines)):
                            if lines[i].strip():  # Only add indentation to non-empty lines
                                lines[i] = indentation + lines[i]
                        new_text = "\n".join(lines)

            return content.replace(old_text, new_text)

        # If exact match fails, try line-by-line matching with whitespace flexibility
        old_lines = old_text.split("\n")
        content_lines = content.split("\n")

        for i in range(len(content_lines) - len(old_lines) + 1):
            potential_match = content_lines[i : i + len(old_lines)]

            # Compare lines with normalized whitespace
            is_match = all(
                old_line.strip() == content_line.strip()
                for old_line, content_line in zip(old_lines, potential_match, strict=False)
            )

            if is_match:
                # Preserve indentation if needed
                if preserve_indentation:
                    # Get original indentation of first line
                    original_indent = ""
                    if i < len(content_lines):
                        original_indent = re.match(r"^\s*", content_lines[i]).group(0)

                    # Apply indentation to new text
                    new_lines = new_text.split("\n")
                    for j in range(len(new_lines)):
                        if j == 0:
                            new_lines[j] = original_indent + new_lines[j].lstrip()
                        else:
                            # For subsequent lines, preserve relative indentation
                            if j < len(old_lines):
                                old_indent = re.match(r"^\s*", old_lines[j]).group(0)
                                new_indent = re.match(r"^\s*", new_lines[j]).group(0)
                                relative_indent = len(new_indent) - len(old_indent)
                                if relative_indent > 0:
                                    # Add extra indentation
                                    new_lines[j] = original_indent + " " * relative_indent + new_lines[j].lstrip()
                                else:
                                    # Use original indentation
                                    new_lines[j] = original_indent + new_lines[j].lstrip()
                            else:
                                # For lines beyond the old text, use original indentation
                                new_lines[j] = original_indent + new_lines[j].lstrip()

                    new_text = "\n".join(new_lines)

                # Replace the matched lines
                content_lines[i : i + len(old_lines)] = new_text.split("\n")
                return "\n".join(content_lines)

        # If we get here, no match was found
        raise ValueError(f"Could not find match for:\n{old_text}")

    async def _create_directory(self, base_directory: str, operation: FileOperation) -> OperationResult:
        """Create a new directory."""
        if not operation.path:
            return OperationResult(type="create_directory", success=False, error="Path not specified")

        try:
            full_path = Path(base_directory) / operation.path
            full_path.mkdir(parents=True, exist_ok=True)
            return OperationResult(type="create_directory", path=operation.path, success=True)
        except Exception as e:
            return OperationResult(
                type="create_directory", path=operation.path, success=False, error=f"Error creating directory: {e}"
            )

    async def _delete_directory(self, base_directory: str, operation: FileOperation) -> OperationResult:
        """Delete a directory."""
        if not operation.path:
            return OperationResult(type="delete_directory", success=False, error="Path not specified")

        try:
            full_path = Path(base_directory) / operation.path
            if not full_path.exists():
                return OperationResult(
                    type="delete_directory",
                    path=operation.path,
                    success=False,
                    error=f"Directory does not exist: {operation.path}",
                )

            if not full_path.is_dir():
                return OperationResult(
                    type="delete_directory",
                    path=operation.path,
                    success=False,
                    error=f"Path is not a directory: {operation.path}",
                )

            shutil.rmtree(full_path)
            return OperationResult(type="delete_directory", path=operation.path, success=True)
        except Exception as e:
            return OperationResult(
                type="delete_directory", path=operation.path, success=False, error=f"Error deleting directory: {e}"
            )

    async def _delete_file(self, base_directory: str, operation: FileOperation) -> OperationResult:
        """Delete a file."""
        if not operation.path:
            return OperationResult(type="delete_file", success=False, error="Path not specified")

        try:
            full_path = Path(base_directory) / operation.path
            if not full_path.exists():
                return OperationResult(
                    type="delete_file",
                    path=operation.path,
                    success=False,
                    error=f"File does not exist: {operation.path}",
                )

            if not full_path.is_file():
                return OperationResult(
                    type="delete_file",
                    path=operation.path,
                    success=False,
                    error=f"Path is not a file: {operation.path}",
                )

            full_path.unlink()
            return OperationResult(type="delete_file", path=operation.path, success=True)
        except Exception as e:
            return OperationResult(
                type="delete_file", path=operation.path, success=False, error=f"Error deleting file: {e}"
            )

    async def _list_directory(self, base_directory: str, operation: FileOperation) -> OperationResult:
        """List contents of a directory."""
        if not operation.path:
            return OperationResult(type="list_directory", success=False, error="Path not specified")

        try:
            full_path = Path(base_directory) / operation.path
            if not full_path.exists():
                return OperationResult(
                    type="list_directory",
                    path=operation.path,
                    success=False,
                    error=f"Directory does not exist: {operation.path}",
                )

            if not full_path.is_dir():
                return OperationResult(
                    type="list_directory",
                    path=operation.path,
                    success=False,
                    error=f"Path is not a directory: {operation.path}",
                )

            entries = list(full_path.iterdir())
            formatted_entries = []

            for entry in entries:
                entry_type = "[DIR]" if entry.is_dir() else "[FILE]"
                formatted_entries.append(f"{entry_type} {entry.name}")

            return OperationResult(
                type="list_directory",
                path=operation.path,
                success=True,
                files=formatted_entries,
                content="\n".join(formatted_entries),
            )
        except Exception as e:
            return OperationResult(
                type="list_directory", path=operation.path, success=False, error=f"Error listing directory: {e}"
            )

    async def _move_file(self, base_directory: str, operation: FileOperation) -> OperationResult:
        """Move or rename a file or directory."""
        source = operation.source
        destination = operation.destination

        if not source or not destination:
            return OperationResult(type="move_file", success=False, error="Source and destination must be specified")

        try:
            full_source = Path(base_directory) / source
            full_destination = Path(base_directory) / destination

            if not full_source.exists():
                return OperationResult(
                    type="move_file", path=source, success=False, error=f"Source does not exist: {source}"
                )

            if full_destination.exists():
                return OperationResult(
                    type="move_file",
                    path=destination,
                    success=False,
                    error=f"Destination already exists: {destination}",
                )

            # Create parent directories if needed
            full_destination.parent.mkdir(parents=True, exist_ok=True)

            # Move the file or directory
            shutil.move(str(full_source), str(full_destination))

            return OperationResult(type="move_file", path=f"{source} -> {destination}", success=True)
        except Exception as e:
            return OperationResult(
                type="move_file", path=f"{source} -> {destination}", success=False, error=f"Error moving file: {e}"
            )

    async def _search_files(self, base_directory: str, operation: FileOperation) -> OperationResult:
        """Search for files matching a pattern."""
        if not operation.path:
            return OperationResult(type="search_files", success=False, error="Base search path not specified")

        if not hasattr(operation, "search_config") or not operation.search_config:
            return OperationResult(type="search_files", success=False, error="Search configuration not specified")

        pattern = operation.search_config.pattern
        exclude_patterns = operation.search_config.exclude_patterns or []

        try:
            full_path = Path(base_directory) / operation.path
            if not full_path.exists():
                return OperationResult(
                    type="search_files",
                    path=operation.path,
                    success=False,
                    error=f"Search path does not exist: {operation.path}",
                )

            if not full_path.is_dir():
                return OperationResult(
                    type="search_files",
                    path=operation.path,
                    success=False,
                    error=f"Search path is not a directory: {operation.path}",
                )

            matches = []

            # Recursive search function
            def search_recursive(directory):
                nonlocal matches
                try:
                    for item in directory.iterdir():
                        # Check if path should be excluded
                        rel_path = item.relative_to(full_path)
                        should_exclude = any(fnmatch(str(rel_path), exclude) for exclude in exclude_patterns)

                        if should_exclude:
                            continue

                        # Check if name matches pattern (case-insensitive)
                        if pattern.lower() in item.name.lower():
                            matches.append(str(item))

                        # Recurse into subdirectories
                        if item.is_dir():
                            search_recursive(item)
                except (PermissionError, OSError):
                    # Skip directories we can't access
                    pass

            # Start search
            search_recursive(full_path)

            if not matches:
                return OperationResult(
                    type="search_files", path=operation.path, success=True, files=[], content="No matches found"
                )

            return OperationResult(
                type="search_files", path=operation.path, success=True, files=matches, content="\n".join(matches)
            )
        except Exception as e:
            return OperationResult(
                type="search_files", path=operation.path, success=False, error=f"Error searching files: {e}"
            )

    async def _get_file_metadata(self, base_directory: str, operation: FileOperation) -> OperationResult:
        """Get detailed information about a file or directory."""
        if not operation.path:
            return OperationResult(type="get_file_metadata", success=False, error="Path not specified")

        try:
            full_path = Path(base_directory) / operation.path
            if not full_path.exists():
                return OperationResult(
                    type="get_file_metadata",
                    path=operation.path,
                    success=False,
                    error=f"Path does not exist: {operation.path}",
                )

            # Get file stats
            stats = full_path.stat()

            # Create FileMetadata object
            file_metadata = FileMetadata(
                size=stats.st_size,
                created=datetime.fromtimestamp(stats.st_ctime).isoformat(),
                modified=datetime.fromtimestamp(stats.st_mtime).isoformat(),
                accessed=datetime.fromtimestamp(stats.st_atime).isoformat(),
                is_directory=full_path.is_dir(),
                is_file=full_path.is_file(),
                permissions=filemode(stats.st_mode),
            )

            # Format as text
            info_text = "\n".join(
                [
                    f"size: {file_metadata.size}",
                    f"created: {file_metadata.created}",
                    f"modified: {file_metadata.modified}",
                    f"accessed: {file_metadata.accessed}",
                    f"is_directory: {file_metadata.is_directory}",
                    f"is_file: {file_metadata.is_file}",
                    f"permissions: {file_metadata.permissions}",
                ]
            )

            return OperationResult(
                type="get_file_metadata",
                path=operation.path,
                success=True,
                file_metadata=file_metadata,
                content=info_text,
            )
        except Exception as e:
            return OperationResult(
                type="get_file_metadata", path=operation.path, success=False, error=f"Error getting file info: {e}"
            )

    def _normalize_line_endings(self, text: str) -> str:
        """Normalize line endings to LF."""
        return text.replace("\r\n", "\n")

    def _create_unified_diff(self, original_content: str, new_content: str, filepath: str = "file") -> str:
        """Create a git-style unified diff."""
        # Ensure consistent line endings for diff
        original_lines = self._normalize_line_endings(original_content).splitlines()
        new_lines = self._normalize_line_endings(new_content).splitlines()

        # Generate unified diff
        diff_lines = list(
            unified_diff(original_lines, new_lines, fromfile=f"a/{filepath}", tofile=f"b/{filepath}", lineterm="")
        )

        # Format with enough backticks to avoid code block issues
        if diff_lines:
            diff_text = "\n".join(diff_lines)
            backtick_count = 3
            while "```" in diff_text:
                backtick_count += 1

            return f"{backtick_count * '`'}\n{diff_text}\n{backtick_count * '`'}"
        else:
            return "```\nNo changes\n```"

    def _preserve_indentation(self, original_text: str, start_idx: int, new_content: str) -> str:
        """Preserve indentation patterns when inserting new content."""
        # Find the line that contains the start position
        last_newline = original_text.rfind("\n", 0, start_idx)
        line_start = last_newline + 1 if last_newline >= 0 else 0

        # Extract leading whitespace from the original line
        leading_space_match = re.match(r"^(\s*)", original_text[line_start:])
        base_indent = leading_space_match.group(1) if leading_space_match else ""

        # Apply indentation to new content lines
        if "\n" in new_content:
            lines = new_content.split("\n")
            # First line gets original indentation
            result = [lines[0]]

            # Subsequent lines get the same base indentation
            for line in lines[1:]:
                if line.strip():  # Only indent non-empty lines
                    result.append(f"{base_indent}{line}")
                else:
                    result.append(line)

            return "\n".join(result)
        else:
            # Single line content
            return new_content
