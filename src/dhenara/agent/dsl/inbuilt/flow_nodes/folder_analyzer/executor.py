import fnmatch
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from stat import filemode
from typing import Literal

from dhenara.agent.dsl.base import (
    ExecutableNodeDefinition,
    ExecutionContext,
    ExecutionStatusEnum,
    NodeID,
    NodeInput,
    NodeOutput,
)
from dhenara.agent.dsl.components.flow import FlowNodeExecutionResult, FlowNodeExecutor
from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.mixin.operations_mixin import FileSytemOperationsMixin
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import (
    DirectoryInfo,
    FileInfo,
    FileMetadata,
    FolderAnalysisOperation,
)
from dhenara.agent.observability.tracing import trace_node
from dhenara.agent.observability.tracing.data import add_trace_attribute

from .input import FolderAnalyzerNodeInput
from .output import (
    FolderAnalysisOperationResult,
    FolderAnalyzerNodeOutcome,
    FolderAnalyzerNodeOutput,
    FolderAnalyzerNodeOutputData,
)
from .settings import FolderAnalyzerSettings
from .tracing import (
    base_directory_attr,
    folder_analyzer_node_tracing_profile,
    operations_count_attr,
    operations_results_attr,
    operations_summary_attr,
)

logger = logging.getLogger(__name__)


class FolderAnalyzerNodeExecutionResult(
    FlowNodeExecutionResult[FolderAnalyzerNodeInput, FolderAnalyzerNodeOutput, FolderAnalyzerNodeOutcome]
):
    pass


class FolderAnalyzerNodeExecutor(FlowNodeExecutor, FileSytemOperationsMixin):
    node_type = FlowNodeTypeEnum.folder_analyzer.value
    input_model = FolderAnalyzerNodeInput
    setting_model = FolderAnalyzerSettings
    _tracing_profile = folder_analyzer_node_tracing_profile

    def get_result_class(self):
        return FolderAnalyzerNodeExecutionResult

    @trace_node(FlowNodeTypeEnum.folder_analyzer.value)
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
    ) -> FolderAnalyzerNodeExecutionResult | None:
        try:
            # Get settings from node definition or input override
            settings = node_definition.select_settings(node_input=node_input)
            if not isinstance(settings, FolderAnalyzerSettings):
                raise ValueError(f"Invalid settings type: {type(settings)}")

            # Get base directory
            base_directory = self.get_formatted_base_directory(
                node_input=node_input,
                settings=settings,
                execution_context=execution_context,
            )
            add_trace_attribute(base_directory_attr, str(base_directory))

            # Get allowed directories
            allowed_directories = self._get_allowed_directories(node_input, settings)

            # Extract operations to perform
            operations = self._extract_operations(
                node_input=node_input,
                settings=settings,
                execution_context=execution_context,
                operation_class=FolderAnalysisOperation,
            )
            if not operations:
                raise ValueError("No folder analysis operations specified")

            # Validate all paths for security
            self._validate_paths(base_directory, operations, allowed_directories, settings.use_relative_paths)

            # Execute operations
            results, success_info, meta_info = await self._execute_operations(
                base_directory=base_directory, operations=operations, settings=settings
            )

            # Create output data
            all_succeeded = success_info["failed_operations"] == 0
            output_data = FolderAnalyzerNodeOutputData(
                base_directory=str(base_directory),
                success=all_succeeded,
                errors=success_info["errors"],
                operations_count=len(operations),
                successful_operations=success_info["successful_operations"],
                failed_operations=success_info["failed_operations"],
                total_files=meta_info["total_files"],
                total_directories=meta_info["total_directories"],
                total_size=meta_info["total_size"],
                file_types=meta_info["file_types"],
                word_count=meta_info["total_word_count"],
                words_read=meta_info["total_words_read"],
            )

            # Create outcome
            outcome = FolderAnalyzerNodeOutcome(
                base_directory=str(base_directory),
                results=results,
            )

            add_trace_attribute(
                operations_summary_attr,
                {
                    "total": len(operations),
                    "successful": success_info["successful_operations"],
                    "failed": success_info["failed_operations"],
                    "all_succeeded": all_succeeded,
                },
            )

            # Create node output
            node_output = NodeOutput[FolderAnalyzerNodeOutputData](data=output_data)

            # Create execution result
            result = FolderAnalyzerNodeExecutionResult(
                node_identifier=node_id,
                execution_status=ExecutionStatusEnum.COMPLETED if all_succeeded else ExecutionStatusEnum.FAILED,
                input=node_input,
                output=node_output,
                outcome=outcome,
                created_at=datetime.now(),
            )

            return result

        except Exception as e:
            logger.exception(f"Folder analyzer execution error: {e}")
            return self.set_node_execution_failed(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
                message=f"Folder analysis failed: {e}",
            )

    async def _execute_operations(
        self,
        base_directory: Path,
        operations: list[FolderAnalysisOperation],
        settings: FolderAnalyzerSettings,
    ) -> tuple[list[FolderAnalysisOperationResult], dict, dict]:
        """
        Execute all folder analysis operations and return results.

        Returns:
            tuple containing:
            - list of FolderAnalysisOperationResult objects
            - dict with success info (successful_operations, failed_operations, errors)
            - dict with meta info (total_files, total_directories, total_size, file_types, total_words_read)
        """
        results = []
        operation_result_trace_data = []
        successful_operations = 0
        failed_operations = 0
        errors = []
        total_word_count = 0
        total_words_read = 0

        total_files = None
        total_directories = None
        total_size = None
        file_types = {}
        total_word_count = 0
        total_words_read = 0

        # Then conditionally set them if include_primary_meta
        if any(op.include_primary_meta for op in operations):
            total_files = 0
            total_directories = 0
            total_size = 0

        add_trace_attribute(operations_count_attr, len(operations))

        for i, operation in enumerate(operations):
            _trace_data = {
                "name": f"operation_{i}",
                "index": i,
                "type": operation.operation_type,
                "path": operation.path,
            }

            try:
                # Validate the operation
                if not operation.validate_content_type():
                    errors = [f"Invalid parameters for operation {operation.operation_type}"]
                    result = FolderAnalysisOperationResult(
                        operation_type=operation.operation_type,
                        path=operation.path,
                        success=False,
                        errors=errors,
                    )
                    errors.extend(errors)
                    failed_operations += 1
                    results.append(result)

                    if settings.fail_fast:
                        break
                    continue

                # Check if operation has multiple paths and process accordingly
                if isinstance(operation.path, list):
                    result = await self._process_multi_path_operation(
                        base_directory=base_directory,
                        operation=operation,
                        settings=settings,
                        total_words_read=total_words_read,
                    )
                else:
                    # Process single path operation based on type
                    if operation.operation_type == "analyze_folder":
                        result = await self._process_analyze_folder_operation(
                            base_directory=base_directory,
                            operation=operation,
                            settings=settings,
                            total_words_read=total_words_read,
                        )
                    elif operation.operation_type == "analyze_file":
                        result = await self._process_analyze_file_operation(
                            base_directory=base_directory,
                            operation=operation,
                            total_words_read=total_words_read,
                        )
                    elif operation.operation_type == "find_files":
                        result = await self._process_find_files_operation(
                            base_directory=base_directory,
                            operation=operation,
                        )
                    elif operation.operation_type in ["get_structure", "get_tree_diagram"]:
                        result = await self._process_get_structure_operation(
                            base_directory=base_directory,
                            operation=operation,
                            settings=settings,
                        )
                    else:
                        result = FolderAnalysisOperationResult(
                            operation_type=operation.operation_type,
                            path=operation.path,
                            success=False,
                            errors=[f"Unsupported operation type: {operation.operation_type}"],
                        )

                # Add result to list
                results.append(result)

                # Update counters
                if result.success:
                    successful_operations += 1

                    # Handle multiple results for multi-path operations
                    if isinstance(result.analysis, list):
                        for analysis in result.analysis:
                            if analysis.word_count is not None:
                                total_word_count += analysis.word_count

                            if operation.include_primary_meta:
                                if analysis.total_files:
                                    total_files += analysis.total_files
                                if analysis.total_directories:
                                    total_directories += analysis.total_directories
                                if analysis.total_size:
                                    total_size += analysis.total_size
                                if analysis.file_types:
                                    for ext, count in analysis.file_types.items():
                                        if ext in file_types:
                                            file_types[ext] += count
                                        else:
                                            file_types[ext] = count
                    elif result.analysis:
                        if result.analysis.word_count is not None:
                            total_word_count += result.analysis.word_count

                        if operation.include_primary_meta:
                            if result.analysis.total_files:
                                total_files += result.analysis.total_files
                            if result.analysis.total_directories:
                                total_directories += result.analysis.total_directories
                            if result.analysis.total_size:
                                total_size += result.analysis.total_size
                            if result.analysis.file_types:
                                for ext, count in result.analysis.file_types.items():
                                    if ext in file_types:
                                        file_types[ext] += count
                                    else:
                                        file_types[ext] = count

                    # Handle multiple file_info results
                    if isinstance(result.file_info, list):
                        for file_info in result.file_info:
                            if file_info.word_count:
                                total_word_count += file_info.word_count
                    elif result.file_info:
                        if result.file_info.word_count:
                            total_word_count += result.file_info.word_count

                    if result.words_read:
                        total_words_read += result.words_read
                else:
                    failed_operations += 1
                    _errors = [result.error] if hasattr(result, "error") else result.errors
                    errors.extend(_errors)
                    if settings.fail_fast:
                        break

            except Exception as e:
                # Handle exceptions for each operation
                errors = [f"Error performing {operation.operation_type} on {operation.path}: {e}"]
                results.append(
                    FolderAnalysisOperationResult(
                        operation_type=operation.operation_type,
                        path=operation.path,
                        success=False,
                        errors=errors,
                    )
                )
                errors.extend(errors)
                failed_operations += 1
                logger.error(errors[0], exc_info=True)
                if settings.fail_fast:
                    break

            # Add operation result to trace
            if i < len(results):
                result = results[i]
                _trace_data.update(
                    {
                        "success": result.success,
                        "errors": errors,
                        "out_type": result.operation_type,
                        "out_path": result.path,
                    },
                )

            # Append trace data
            operation_result_trace_data.append(_trace_data)

        # Add trace data
        add_trace_attribute(operations_results_attr, operation_result_trace_data)

        success_info = {
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "errors": errors,
        }

        meta_info = {
            "total_files": total_files,
            "total_directories": total_directories,
            "total_size": total_size,
            "file_types": file_types,
            "total_word_count": total_word_count,
            "total_words_read": total_words_read,
        }

        return results, success_info, meta_info

    async def _process_multi_path_operation(
        self,
        base_directory: Path,
        operation: FolderAnalysisOperation,
        settings: FolderAnalyzerSettings,
        total_words_read: int,
    ) -> FolderAnalysisOperationResult:
        """Process an operation with multiple paths"""
        path_list = operation.path if isinstance(operation.path, list) else [operation.path]

        all_analysis = []
        all_file_info = []
        all_files_found = []
        all_tree_diagrams = []
        all_errors = []
        total_words_read_multi = 0
        success = True

        for single_path in path_list:
            # Create a single-path operation
            single_path_operation = FolderAnalysisOperation(**{**operation.model_dump(), "path": single_path})

            try:
                if operation.operation_type == "analyze_folder":
                    single_result = await self._process_analyze_folder_operation(
                        base_directory=base_directory,
                        operation=single_path_operation,
                        settings=settings,
                        total_words_read=total_words_read + total_words_read_multi,
                    )
                elif operation.operation_type == "analyze_file":
                    single_result = await self._process_analyze_file_operation(
                        base_directory=base_directory,
                        operation=single_path_operation,
                        total_words_read=total_words_read + total_words_read_multi,
                    )
                elif operation.operation_type == "find_files":
                    single_result = await self._process_find_files_operation(
                        base_directory=base_directory,
                        operation=single_path_operation,
                    )
                elif operation.operation_type in ["get_structure", "get_tree_diagram"]:
                    single_result = await self._process_get_structure_operation(
                        base_directory=base_directory,
                        operation=single_path_operation,
                        settings=settings,
                    )
                else:
                    single_result = FolderAnalysisOperationResult(
                        operation_type=operation.operation_type,
                        path=single_path,
                        success=False,
                        errors=[f"Unsupported operation type: {operation.operation_type}"],
                    )

                if single_result.success:
                    if single_result.analysis:
                        all_analysis.append(single_result.analysis)
                    if single_result.file_info:
                        all_file_info.append(single_result.file_info)
                    if single_result.files_found:
                        all_files_found.extend(single_result.files_found)
                    if single_result.tree_diagram:
                        all_tree_diagrams.append(f"# {single_path}\n{single_result.tree_diagram}")
                    if single_result.words_read:
                        total_words_read_multi += single_result.words_read
                else:
                    success = False
                    if single_result.errors:
                        all_errors.extend(single_result.errors)

            except Exception as e:
                success = False
                all_errors.append(f"Error processing path {single_path}: {e}")

        # Combine results
        combined_result = FolderAnalysisOperationResult(
            operation_type=operation.operation_type,
            path=operation.path,  # Keep original list
            success=success,
            errors=all_errors if all_errors else None,
            words_read=total_words_read_multi if total_words_read_multi > 0 else None,
        )

        # Set appropriate result fields based on operation type
        if all_analysis:
            combined_result.analysis = all_analysis if len(all_analysis) > 1 else all_analysis[0]
        if all_file_info:
            combined_result.file_info = all_file_info if len(all_file_info) > 1 else all_file_info[0]
        if all_files_found:
            combined_result.files_found = all_files_found
        if all_tree_diagrams:
            combined_result.tree_diagram = "\n\n".join(all_tree_diagrams)

        return combined_result

    async def _process_analyze_folder_operation(
        self,
        base_directory: Path,
        operation: FolderAnalysisOperation,
        settings: FolderAnalyzerSettings,
        total_words_read: int,
    ) -> FolderAnalysisOperationResult:
        """Process an analyze_folder operation"""
        # Get path info
        path_info = self._get_operation_path_info(base_directory, operation, settings)

        if not path_info["success"]:
            return FolderAnalysisOperationResult(
                operation_type="analyze_folder",
                path=path_info["path_str"],
                success=False,
                errors=[path_info["error"]],
            )

        path = path_info["path"]
        path_str = path_info["path_str"]
        exclude_patterns = path_info["exclude_patterns"]

        # Check if directory
        if not path.is_dir():
            return FolderAnalysisOperationResult(
                operation_type="analyze_folder",
                path=path_str,
                success=False,
                errors=[f"Path is not a directory: {path_str}"],
            )

        # Analyze folder
        analysis, words_read = self._analyze_folder(
            path=path,
            base_directory=base_directory,
            operation=operation,
            settings=settings,
            exclude_patterns=exclude_patterns,
            current_depth=0,
            total_words_read=total_words_read,
        )

        # Generate tree diagram if requested
        tree_diagram = None
        if operation.generate_tree_diagram:
            tree_diagram = self._generate_tree_diagram(
                path=path,
                operation=operation,
                exclude_patterns=exclude_patterns,
            )

        # Return result
        return FolderAnalysisOperationResult(
            operation_type="analyze_folder",
            path=path_str,
            success=True,
            analysis=analysis,
            tree_diagram=tree_diagram,
            words_read=words_read,
        )

    async def _process_analyze_file_operation(
        self, base_directory: Path, operation: FolderAnalysisOperation, total_words_read: int
    ) -> FolderAnalysisOperationResult:
        """Process an analyze_file operation"""
        # Get path info
        path_info = self._get_operation_path_info(base_directory, operation)

        if not path_info["success"]:
            return FolderAnalysisOperationResult(
                operation_type="analyze_file",
                path=path_info["path_str"],
                success=False,
                errors=[path_info["error"]],
            )

        path = path_info["path"]
        path_str = path_info["path_str"]

        # Check if file
        if not path.is_file():
            return FolderAnalysisOperationResult(
                operation_type="analyze_file",
                path=path_str,
                success=False,
                errors=[f"Path is not a file: {path_str}"],
            )

        # Analyze file
        file_info, words_read = self._analyze_file(
            path=path,
            base_directory=base_directory,
            operation=operation,
            force_skip_content=not operation.read_content,
        )

        # Return result
        return FolderAnalysisOperationResult(
            operation_type="analyze_file",
            path=path_str,
            success=True,
            file_info=file_info,
            words_read=words_read,
        )

    async def _process_find_files_operation(
        self, base_directory: Path, operation: FolderAnalysisOperation
    ) -> FolderAnalysisOperationResult:
        """Process a find_files operation"""
        # Get path info
        path_info = self._get_operation_path_info(base_directory, operation)

        if not path_info["success"]:
            return FolderAnalysisOperationResult(
                operation_type="find_files",
                path=path_info["path_str"],
                success=False,
                errors=[path_info["error"]],
            )

        path = path_info["path"]
        path_str = path_info["path_str"]
        exclude_patterns = path_info["exclude_patterns"]

        # Check if directory
        if not path.is_dir():
            return FolderAnalysisOperationResult(
                operation_type="find_files",
                path=path_str,
                success=False,
                errors=[f"Path is not a directory: {path_str}"],
            )

        # Find files
        found_files = []
        total_size = 0

        # Recursive function to find files
        def find_files_recursive(current_path, current_depth=0):
            nonlocal found_files, total_size

            if operation.max_depth is not None and current_depth > operation.max_depth:
                return

            try:
                for item in current_path.iterdir():
                    # Skip hidden files/dirs if not included
                    if not operation.include_hidden and item.name.startswith("."):
                        continue

                    # Skip excluded patterns
                    if any(fnmatch.fnmatch(item.name, pattern) for pattern in exclude_patterns):
                        continue

                    # Process files
                    if item.is_file():
                        rel_path = self._get_path_str_for_result(
                            path=item,
                            base_directory=base_directory,
                            use_relative_paths=True,
                            include_root_in_path=operation.include_root_in_path,
                        )
                        found_files.append(rel_path)

                        try:
                            total_size += item.stat().st_size
                        except (PermissionError, OSError):
                            pass

                    # Process directories recursively
                    elif item.is_dir():
                        find_files_recursive(item, current_depth + 1)

            except (PermissionError, OSError) as e:
                logger.error(f"Error accessing {current_path}: {e}")

        # Start recursive search
        find_files_recursive(path)

        # Return result
        return FolderAnalysisOperationResult(
            operation_type="find_files",
            path=path_str,
            success=True,
            files_found=found_files,
        )

    async def _process_get_structure_operation(
        self,
        base_directory: Path,
        operation: FolderAnalysisOperation,
        settings: FolderAnalyzerSettings,
    ) -> FolderAnalysisOperationResult:
        """Process a get_structure operation - returns directory structure without file contents"""
        # Create a non-content operation

        # non_content_operation = FolderAnalysisOperation(
        #    **{
        #        **operation.model_dump(),
        #        "read_content": False,
        #        "include_content_preview": False,
        #    },
        # )

        non_content_operation = operation

        # Get path info
        path_info = self._get_operation_path_info(base_directory, operation, settings)

        if not path_info["success"]:
            return FolderAnalysisOperationResult(
                operation_type="get_structure",
                path=path_info["path_str"],
                success=False,
                errors=[path_info["error"]],
            )

        path = path_info["path"]
        path_str = path_info["path_str"]
        exclude_patterns = path_info["exclude_patterns"]

        # Generate tree diagram
        tree_diagram = None
        if non_content_operation.generate_tree_diagram or non_content_operation.operation_type == "get_tree_diagram":
            tree_diagram = self._generate_tree_diagram(
                path=path,
                operation=non_content_operation,
                exclude_patterns=exclude_patterns,
            )

        if non_content_operation.operation_type == "get_tree_diagram":
            return FolderAnalysisOperationResult(
                operation_type="get_structure",
                path=path_str,
                success=True,
                analysis=None,
                tree_diagram=tree_diagram,
            )

        # If it's a directory, get the structure
        if path.is_dir():
            analysis, _ = self._analyze_folder(
                path=path,
                base_directory=base_directory,
                operation=non_content_operation,
                settings=settings,
                exclude_patterns=exclude_patterns,
                current_depth=0,
                total_words_read=0,
            )

            return FolderAnalysisOperationResult(
                operation_type="get_structure",
                path=path_str,
                success=True,
                analysis=analysis,
                tree_diagram=tree_diagram,
                errors=analysis.errors,
            )

        # If it's a file, return file info
        elif path.is_file():
            file_info, _ = self._analyze_file(
                path=path,
                base_directory=base_directory,
                operation=non_content_operation,
                force_skip_content=True,
            )

            return FolderAnalysisOperationResult(
                operation_type="get_structure",
                path=path_str,
                success=True,
                file_info=file_info,
            )
        else:
            return FolderAnalysisOperationResult(
                operation_type="get_structure",
                path=path_str,
                success=False,
                errors=[f"Path is neither a file nor a directory: {path_str}"],
            )

    def _get_operation_path_info(
        self,
        base_directory: Path,
        operation: FolderAnalysisOperation,
        settings: FolderAnalyzerSettings = None,
    ) -> dict:
        """Get path information for an operation with proper error handling"""
        # Convert path to Path object - handle both str and list[str]
        try:
            operation_path = operation.path
            if isinstance(operation_path, list):
                # For multi-path operations, use the first path for validation
                operation_path = operation_path[0]

            if Path(operation_path).is_absolute():
                path = Path(operation_path).resolve()
            else:
                path = (base_directory / operation_path).resolve()

            use_relative_paths = True
            if settings and hasattr(settings, "use_relative_paths"):
                use_relative_paths = settings.use_relative_paths

            # Format path for result
            path_str = self._get_path_str_for_result(
                path=path,
                base_directory=base_directory,
                use_relative_paths=use_relative_paths,
                include_root_in_path=operation.include_root_in_path,
            )

            # Check if path exists
            if not path.exists():
                return {
                    "success": False,
                    "path": path,
                    "path_str": path_str,
                    "error": f"Path does not exist: {path_str}",
                    "exclude_patterns": [],
                }

            # Get exclude patterns including gitignore if needed
            exclude_patterns = list(operation.exclude_patterns)
            if operation.respect_gitignore:
                # Look for gitignores in the base dir and the current operation dir
                gitignore_patterns = self._parse_gitignore(base_directory)
                gitignore_patterns += self._parse_gitignore(path)

                # Add patterns from additional gitignore files if specified
                if operation.additional_gitignore_paths:
                    for gitignore_path_str in operation.additional_gitignore_paths:
                        # Convert the gitignore path to a Path object
                        if Path(gitignore_path_str).is_absolute():
                            gitignore_path = Path(gitignore_path_str).resolve()
                        else:
                            gitignore_path = (base_directory / gitignore_path_str).resolve()

                        # Parse the additional gitignore file
                        if gitignore_path.exists() and gitignore_path.is_file():
                            gitignore_patterns += self._parse_gitignore(gitignore_path.parent)

                exclude_patterns.extend(gitignore_patterns)

            return {
                "success": True,
                "path": path,
                "path_str": path_str,
                "exclude_patterns": exclude_patterns,
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "path": None,
                "path_str": str(operation.path),
                "error": f"Error processing path: {e}",
                "exclude_patterns": [],
            }

    def _parse_gitignore(self, path: Path) -> list[str]:
        """Parse .gitignore files and return patterns to exclude."""
        patterns = []
        gitignore_path = path / ".gitignore"

        if gitignore_path.exists() and gitignore_path.is_file():
            try:
                with open(gitignore_path) as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if not line or line.startswith("#"):
                            continue
                        # Skip negated patterns (for simplicity)
                        if line.startswith("!"):
                            continue
                        patterns.append(line)
            except Exception as e:
                logger.error(f"Error parsing .gitignore file: {e}")

        return patterns

    def _should_exclude(self, path: Path, exclude_patterns: list[str], include_hidden: bool) -> bool:
        """
        Check if a path should be excluded based on patterns and hidden status.

        Args:
            path: The path to check
            exclude_patterns: List of exclusion patterns
            include_hidden: Whether to include hidden files/directories
        """
        # Check for hidden files/directories
        if not include_hidden and path.name.startswith("."):
            return True

        # For simple filename patterns (no path separators)
        if any("/" not in pattern and fnmatch.fnmatch(path.name, pattern) for pattern in exclude_patterns):
            # prnt(f"Excluding {path}: matched filename pattern")
            return True

        # For path-based patterns
        str_path = str(path)
        for pattern in exclude_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith("/"):
                pattern = pattern.rstrip("/")
                if path.is_dir() and str_path.endswith(pattern):
                    # prnt(f"Excluding {path}: matched directory pattern {pattern}")
                    return True

            # General path pattern matching
            elif "/" in pattern:
                # Check if pattern is a substring of the path
                if pattern in str_path:
                    # prnt(f"Excluding {path}: matched path pattern {pattern}")
                    return True

                # Also try fnmatch for glob patterns
                path_parts = str_path.split("/")
                pattern_parts = pattern.split("/")

                # Try to match the end of the path
                if len(path_parts) >= len(pattern_parts):
                    path_suffix = "/".join(path_parts[-len(pattern_parts) :])
                    if fnmatch.fnmatch(path_suffix, pattern):
                        # prnt(f"Excluding {path}: matched path suffix pattern {pattern}")
                        return True

        return False

    def _analyze_folder(
        self,
        path: Path,
        base_directory: Path,
        operation: FolderAnalysisOperation,
        settings: FolderAnalyzerSettings,
        exclude_patterns: list[str],
        current_depth: int,
        total_words_read: int,
    ) -> tuple[DirectoryInfo, int]:
        """
        Recursively analyze a folder structure with enhanced options.
        Returns DirectoryInfo and stats.
        """
        # Check max depth
        if operation.max_depth is not None and current_depth > operation.max_depth:
            return DirectoryInfo(
                path=str(path),
                truncated=True,
            ), 0

        # Format path for result
        path_str = self._get_path_str_for_result(
            path=path,
            base_directory=base_directory,
            use_relative_paths=settings.use_relative_paths,
            include_root_in_path=operation.include_root_in_path,
        )

        result = DirectoryInfo(
            path=path_str,
            children=[],
        )

        # Initialize errors list if needed
        if result.errors is None:
            result.errors = []

        # Include stats if requested
        if operation.include_stats_and_meta:
            try:
                stat = path.stat()
                result.size = stat.st_size
                result.created = datetime.fromtimestamp(stat.st_ctime).isoformat()
                result.modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                result.accessed = datetime.fromtimestamp(stat.st_atime).isoformat()
                result.permissions = filemode(stat.st_mode)
                result.total_size = 0
            except (PermissionError, OSError) as e:
                errors = [f"Failed to get stats for {path}: {e}"]
                result.errors.extend(errors)

        # Initialize counters properly
        file_count = 0 if operation.include_primary_meta else None
        dir_count = 0 if operation.include_primary_meta else None

        # Initialize total counters properly
        if operation.include_primary_meta:
            result.total_files = 0
            result.total_directories = 0
            result.total_size = 0
            result.file_types = {}  # Initialize file_types dictionary

        total_words_read = 0

        try:
            for item in path.iterdir():
                # Check if item should be excluded
                if self._should_exclude(item, exclude_patterns, operation.include_hidden):
                    continue

                if item.is_dir():
                    if file_count is not None:
                        dir_count += 1

                    if operation.include_primary_meta:
                        result.total_directories += 1

                    # Recursively analyze subdirectory
                    child_result, words_read = self._analyze_folder(
                        path=item,
                        base_directory=base_directory,
                        operation=operation,
                        settings=settings,
                        exclude_patterns=exclude_patterns,
                        current_depth=current_depth + 1,
                        total_words_read=total_words_read,
                    )

                    # Merge stats
                    total_words_read += words_read
                    if operation.include_primary_meta:
                        result.total_files += child_result.total_files or 0
                        result.total_directories += child_result.total_directories or 0
                        result.total_size += child_result.total_size or 0

                        # Merge file types
                        if child_result.file_types:
                            if result.file_types is None:
                                result.file_types = {}
                            for ext, count in child_result.file_types.items():
                                result.file_types[ext] = result.file_types.get(ext, 0) + count

                    # Merge errors
                    if child_result.errors:
                        result.errors.extend(child_result.errors)
                    result.children.append(child_result)

                elif item.is_file():
                    if file_count is not None:
                        file_count += 1

                    if operation.include_primary_meta:
                        result.total_files += 1

                    # Check if we've reached the word limit
                    if operation.max_total_words and total_words_read + result.words_read >= operation.max_total_words:
                        # Skip reading content if we've reached the total word limit
                        file_result, _ = self._analyze_file(
                            path=item,
                            base_directory=base_directory,
                            operation=operation,
                            force_skip_content=True,
                        )
                    else:
                        # Analyze file with regular settings
                        file_result, words_read = self._analyze_file(
                            path=item,
                            base_directory=base_directory,
                            operation=operation,
                        )
                        total_words_read += words_read

                    if operation.include_primary_meta:
                        # Update file type stats
                        ext = item.suffix.lower()
                        if result.file_types is None:
                            result.file_types = {}
                        if ext in result.file_types:
                            result.file_types[ext] += 1
                        else:
                            result.file_types[ext] = 1

                    if file_result.metadata and file_result.metadata.size:
                        if result.total_size is not None:
                            result.total_size += file_result.metadata.size

                    if file_result.error:
                        if result.errors is None:
                            result.errors = []
                        result.errors.append(file_result.error)

                    result.children.append(file_result)

            # Add counts to result
            result.file_count = file_count
            result.dir_count = dir_count

            # Reset errors to None if there are not errors, so that this field will be excluded in model_dump()
            if not result.errors:
                result.errors = None

            return result, total_words_read

        except (PermissionError, OSError) as e:
            error_msg = f"Failed to read directory {path}: {e}"
            if result.errors is None:
                result.errors = [error_msg]
            else:
                result.errors.append(error_msg)
            return result, total_words_read

    def _analyze_file(
        self,
        path: Path,
        base_directory: Path,
        operation: FolderAnalysisOperation,
        force_skip_content: bool = False,
    ) -> tuple[FileInfo, int]:
        """
        Analyze a single file with enhanced options.
        Returns FileInfo and number of words read.
        """
        # Format path for result
        path_str = self._get_path_str_for_result(
            path=path,
            base_directory=base_directory,
            use_relative_paths=True,
            include_root_in_path=operation.include_root_in_path,
        )

        result = FileInfo(
            path=path_str,
        )

        # Include stats if requested
        if operation.include_stats_and_meta:
            try:
                stat = path.stat()
                result.metadata = FileMetadata(
                    size=stat.st_size,
                    created=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    accessed=datetime.fromtimestamp(stat.st_atime).isoformat(),
                    is_directory=path.is_dir(),
                    is_file=path.is_file(),
                    permissions=filemode(stat.st_mode),
                )
            except (PermissionError, OSError) as e:
                result.error = f"Failed to get stats: {e}"

        # Skip content analysis if requested
        if force_skip_content:
            return result, 0

        # Track words read
        words_read = 0
        truncated = None

        # Use unix cmds to get wordcount irrespective of the content_read_mode
        if operation.include_primary_meta:
            try:
                result.word_count = self.word_count(path)
            except Exception as e:
                logger.debug(f"Error getting word count: {e}")

        should_read_content = operation.include_content_preview or operation.read_content
        if should_read_content:
            if operation.content_read_mode == "structure" and path.suffix.lower() == ".py":
                from .helpers.python_extractor import PythonStructureExtractor

                try:
                    # Use Python's built-in ast module
                    extractor = PythonStructureExtractor(path)
                    structure = extractor.extract(detail_level=operation.content_structure_detail_level)

                    formatted_structure = [f"{key}: {value}" for key, value in structure.items()]
                    result.content_structure = "\n\n".join(formatted_structure)

                    words_read = len(result.content_structure.split())

                except Exception as e:
                    # Fallback to regular content processing
                    result.error = f"Failed to extract structure: {e}"

            elif (
                operation.content_read_mode == "smart_chunks"
                and hasattr(operation, "use_langchain_splitter")
                and operation.use_langchain_splitter
            ):
                # TODO_FUTURE: Not functional
                from .helpers.helper_fns import optimize_for_llm_context

                try:
                    result.content = optimize_for_llm_context(path, operation)
                    words_read = len(result.content.split())
                except Exception as e:
                    result.error = f"Smart chunking failed: {e}"

        # Fallback to original method for other modes or when other methods fail
        if should_read_content and (operation.content_read_mode == "full" or not result.content_structure):
            # Check file size limit
            file_size = result.metadata.size if result.metadata else 0
            if operation.max_file_size is None or file_size <= operation.max_file_size:
                mime_type = None
                is_text = None
                try:
                    # Get mime type
                    mime_type, _ = mimetypes.guess_type(str(path))

                    # For text files, try to determine encoding and sample content
                    _is_likely_text = mime_type and (
                        mime_type.startswith("text/")
                        or mime_type
                        in [
                            "application/json",
                            "application/xml",
                            "application/javascript",
                            "application/x-python",
                        ]
                    )

                    # Handle image files
                    if mime_type and mime_type.startswith("image/"):
                        try:
                            with open(path, "rb") as img_file:
                                image_bytes = img_file.read()
                                result.content = image_bytes
                                is_text = False
                        except Exception as e:
                            result.error = f"Error reading image file: {e}"
                            is_text = False

                    # Handle text and other files
                    else:
                        try:
                            with open(path, encoding="utf-8") as f:
                                if operation.read_content:
                                    # Read full content
                                    content = f.read()

                                    # Apply content exclusions if specified
                                    if operation.content_exclusions and operation.content_read_mode == "full":
                                        content = self._apply_content_exclusions(
                                            content,
                                            path.suffix.lower(),
                                            operation.content_exclusions,
                                        )

                                    # Apply word limit per file if specified
                                    if operation.max_words_per_file:
                                        words = content.split()
                                        if len(words) > operation.max_words_per_file:
                                            truncated = True
                                            content = " ".join(words[: operation.max_words_per_file])
                                            content += f"\n... [truncated after {operation.max_words_per_file} words]"

                                    # Track words read
                                    words_read = len(content.split())

                                    # Add content to result
                                    result.content = content

                                elif operation.include_content_preview:
                                    # Just read first few lines for preview
                                    content_preview = "".join(f.readline() for _ in range(5))
                                    result.content_preview = content_preview

                                # TODO_FUTURE
                                ## Generate a summary if requested
                                # if operation.generate_file_summary:
                                #    summary = self._generate_file_summary(
                                #        path, result.content or result.content_preview
                                #    )
                                #    result.summary = summary

                                is_text = True
                        except UnicodeDecodeError:
                            is_text = False
                        except Exception as e:
                            result.error = f"Error reading file: {e}"
                            is_text = False
                except Exception as e:
                    result.error = f"Error analyzing content: {e}"

                if truncated is not None:
                    result.truncated = truncated

                if operation.include_primary_meta:
                    result.mime_type = mime_type or "application/octet-stream"
                    result.is_text = is_text

        return result, words_read

    def _apply_content_exclusions(
        self,
        content: str,
        file_extension: str,
        exclusions: list[Literal["doc_strings", "comments", "blank_lines"]],
    ) -> str:
        """
        Apply content exclusions to file content.

        Args:
            content: The file content
            file_extension: The file extension (e.g. ".py")
            exclusions: List of exclusion types

        Returns:
            Modified content with specified elements excluded
        """
        if not exclusions:
            return content

        # Process different file types
        if file_extension in [".py"]:
            # Python-specific processing
            if "doc_strings" in exclusions:
                content = self._remove_python_docstrings(content)
            if "comments" in exclusions:
                content = self._remove_python_comments(content)
        elif file_extension in [".js", ".ts", ".java", ".c", ".cpp", ".go"]:
            # C-style comments
            if "doc_strings" in exclusions or "comments" in exclusions:
                content = self._remove_c_style_comments(content)

        # Language-agnostic processing
        if "blank_lines" in exclusions:
            # Remove blank lines
            content = "\n".join(line for line in content.splitlines() if line.strip())

        return content

    def _remove_python_docstrings(self, content: str) -> str:
        """Remove Python docstrings from content."""
        import re

        # Pattern for triple single or double quotes docstrings
        pattern = r"(\'\'\'[\s\S]*?\'\'\'|\"\"\"[\s\S]*?\"\"\")"
        return re.sub(pattern, "", content)

    def _remove_python_comments(self, content: str) -> str:
        """Remove Python single-line and inline comments."""
        result = []
        for line in content.splitlines():
            # Find hash character that isn't in a string
            comment_pos = -1
            in_single_quote = False
            in_double_quote = False

            for i, char in enumerate(line):
                if char == "'" and (i == 0 or line[i - 1] != "\\"):
                    in_single_quote = not in_single_quote
                elif char == '"' and (i == 0 or line[i - 1] != "\\"):
                    in_double_quote = not in_double_quote
                elif char == "#" and not in_single_quote and not in_double_quote:
                    comment_pos = i
                    break

            if comment_pos >= 0:
                # Keep the part before the comment
                result.append(line[:comment_pos])
            else:
                result.append(line)

        return "\n".join(result)

    def _remove_c_style_comments(self, content: str) -> str:
        """Remove C-style comments (/* ... */ and // ...)."""
        import re

        # First remove multi-line comments
        content = re.sub(r"/\*[\s\S]*?\*/", "", content)
        # Then remove single-line comments
        result = []
        for line in content.splitlines():
            comment_pos = line.find("//")
            if comment_pos >= 0:
                # Check if // is inside a string
                in_string = False
                string_char = None
                escape = False
                valid_comment = True

                for _i, char in enumerate(line[:comment_pos]):
                    if escape:
                        escape = False
                        continue

                    if char == "\\":
                        escape = True
                    elif in_string and char == string_char:
                        in_string = False
                    elif not in_string and (char == '"' or char == "'"):
                        in_string = True
                        string_char = char

                if in_string:
                    # // is inside a string, keep the whole line
                    valid_comment = False

                if valid_comment:
                    result.append(line[:comment_pos])
                else:
                    result.append(line)
            else:
                result.append(line)

        return "\n".join(result)

    def word_count(self, filepath):
        """Get the word count of a file using wc command"""
        import subprocess

        try:
            result = subprocess.run(["wc", "-w", filepath], capture_output=True, text=True)
            if result.returncode == 0:
                return int(result.stdout.split()[0])
            return 0
        except Exception:
            # Fallback if wc command fails
            try:
                with open(filepath, encoding="utf-8") as f:
                    return len(f.read().split())
            except Exception:
                return 0

    def _generate_file_summary(self, path: Path, content: str | None) -> str:
        """Generate a simple summary of the file content."""
        if not content:
            return "Empty file"

        # Get file extension
        ext = path.suffix.lower()

        # Basic summary based on file type
        if ext in [".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rb"]:
            # For code files, extract imports and classes/functions
            summary_lines = []

            # Look for imports
            import_lines = []
            for line in content.splitlines()[:30]:  # Look only in the first 30 lines
                if ext == ".py" and (line.startswith("import ") or line.startswith("from ")):
                    import_lines.append(line)
                elif ext in [".js", ".ts"] and (line.strip().startswith("import ") or "require(" in line):
                    import_lines.append(line)
                elif ext == ".java" and (line.strip().startswith("import ")):
                    import_lines.append(line)

            if import_lines:
                summary_lines.append(f"Contains {len(import_lines)} imports/dependencies")

            # Look for classes/functions
            class_count = 0
            function_count = 0
            for line in content.splitlines():
                line = line.strip()
                if ext == ".py":
                    if line.startswith("class "):
                        class_count += 1
                    elif line.startswith("def "):
                        function_count += 1
                elif ext in [".js", ".ts"]:
                    if line.startswith("class ") or "class " in line:
                        class_count += 1
                    elif line.startswith("function ") or " function " in line:
                        function_count += 1
                elif ext == ".java":
                    if line.startswith("class ") or line.startswith("interface "):
                        class_count += 1
                    elif "public " in line and "(" in line and ")" in line:
                        function_count += 1

            if class_count > 0:
                summary_lines.append(f"Contains {class_count} classes/interfaces")
            if function_count > 0:
                summary_lines.append(f"Contains {function_count} functions/methods")

            # Get total lines of code
            line_count = len(content.splitlines())
            summary_lines.append(f"Total lines: {line_count}")

            return "\n".join(summary_lines)

        elif ext in [".md", ".txt", ".rst"]:
            # For text files, summarize first few lines
            lines = content.splitlines()
            first_line = lines[0] if lines else ""
            return (
                f"Text document: {first_line[:50]}{'' if len(first_line) <= 50 else '...'}\nTotal lines: {len(lines)}"
            )

        elif ext in [".json", ".yaml", ".yml"]:
            # For data files, count keys at the top level
            try:
                if ext == ".json":
                    import json

                    data = json.loads(content)
                    if isinstance(data, dict):
                        return f"JSON with {len(data)} top-level keys"
                    elif isinstance(data, list):
                        return f"JSON array with {len(data)} items"
                    else:
                        return "JSON data (scalar value)"
                elif ext in [".yaml", ".yml"]:
                    # Simple line count for YAML
                    return f"YAML file with {len(content.splitlines())} lines"
            except Exception:
                pass

            # Fallback for non-parseable files
            return f"Data file with {len(content.splitlines())} lines"

        else:
            # Generic summary for other files
            line_count = len(content.splitlines())
            word_count = len(content.split())
            return f"File contains {line_count} lines and approximately {word_count} words"

    def _get_path_str_for_result(
        self,
        path: Path,
        base_directory: Path,
        use_relative_paths: bool,
        include_root_in_path: bool,
    ) -> str:
        """Format a path according to the specified settings."""
        if use_relative_paths:
            try:
                # Get the relative path from the root
                rel_path = path.relative_to(base_directory)

                # Handle the root directory case
                if str(rel_path) == ".":
                    if include_root_in_path:
                        return path.name
                    else:
                        return "."

                # For other paths, add the root name if requested
                if include_root_in_path:
                    return str(Path(base_directory.name) / rel_path)
                else:
                    return str(rel_path)
            except ValueError:
                # If the path is not relative to the root (shouldn't happen), fall back to absolute
                return str(path)
        else:
            # Return the absolute path
            return str(path)

    def _generate_tree_diagram(
        self,
        path: Path,
        operation: FolderAnalysisOperation,
        exclude_patterns: list[str],
    ) -> str:
        """Generate a human-readable ASCII tree diagram of the directory structure."""
        tree_lines = []
        max_depth = operation.tree_diagram_max_depth or operation.max_depth

        # Store the root directory name
        root_name = path.name or str(path)
        tree_lines.append(root_name)

        # Process the directory structure
        self._build_tree_diagram(
            path=path,
            prefix="",
            tree_lines=tree_lines,
            exclude_patterns=exclude_patterns,
            operation=operation,
            current_depth=0,
            max_depth=max_depth,
        )

        return "\n".join(tree_lines)

    def _build_tree_diagram(
        self,
        path: Path,
        prefix: str,
        tree_lines: list[str],
        exclude_patterns: list[str],
        operation: FolderAnalysisOperation,
        current_depth: int,
        max_depth: int | None,
    ) -> None:
        """Recursively build the tree diagram."""
        if max_depth is not None and current_depth >= max_depth:
            return

        # Get all items in the directory
        try:
            items = list(path.iterdir())

            # Sort: directories first, then files
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

            # Process each item
            for i, item in enumerate(items):
                # Skip excluded items
                if self._should_exclude(item, exclude_patterns, operation.include_hidden):
                    continue

                # Determine if this is the last item at this level
                is_last = i == len(items) - 1

                # Set the appropriate prefix characters
                if is_last:
                    branch = "└── "
                    new_prefix = prefix + "    "
                else:
                    branch = "├── "
                    new_prefix = prefix + "│   "

                # Add the item to the tree
                tree_lines.append(f"{prefix}{branch}{item.name}")

                # Recursively process directories
                if item.is_dir():
                    self._build_tree_diagram(
                        path=item,
                        prefix=new_prefix,
                        tree_lines=tree_lines,
                        exclude_patterns=exclude_patterns,
                        operation=operation,
                        current_depth=current_depth + 1,
                        max_depth=max_depth,
                    )
                # Skip files if requested
                elif not item.is_file() or not operation.tree_diagram_include_files:
                    continue

        except (PermissionError, OSError) as e:
            # Handle access errors
            tree_lines.append(f"{prefix}├── [Error: {e}]")
