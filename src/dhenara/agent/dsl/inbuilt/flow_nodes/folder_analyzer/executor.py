import fnmatch
import json
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from stat import filemode
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
from dhenara.agent.dsl.components.flow import FlowNodeExecutor
from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.mixin.operations_mixin import FileSytemOperationsMixin
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import (
    DirectoryInfo,
    FileInfo,
    FileMetadata,
    FolderAnalysisOperation,
)
from dhenara.agent.observability.tracing import trace_node
from dhenara.agent.observability.tracing.data import TracingDataCategory, add_trace_attribute

from .input import FolderAnalyzerNodeInput
from .output import (
    FolderAnalysisOperationResult,
    FolderAnalyzerNodeOutcome,
    FolderAnalyzerNodeOutput,
    FolderAnalyzerNodeOutputData,
)
from .settings import FolderAnalyzerSettings
from .tracing import folder_analyzer_node_tracing_profile

logger = logging.getLogger(__name__)

FolderAnalyzerNodeExecutionResult = NodeExecutionResult[
    FolderAnalyzerNodeInput,
    FolderAnalyzerNodeOutput,
    FolderAnalyzerNodeOutcome,
]


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
            results, successful_operations, failed_operations, errors, meta = await self._execute_operations(
                base_directory, operations, settings
            )

            # Create output data
            all_succeeded = failed_operations == 0

            output_data = FolderAnalyzerNodeOutputData(
                base_directory=str(base_directory),
                success=all_succeeded,
                errors=errors,
                operations_count=len(operations),
                successful_operations=successful_operations,
                failed_operations=failed_operations,
                total_files=meta["total_files"],
                total_directories=meta["total_directories"],
                total_size=meta["total_size"],
                file_types=meta["file_types"],
                total_words_read=meta["total_words_read"],
            )

            # Create outcome
            outcome = FolderAnalyzerNodeOutcome(
                base_directory=str(base_directory),
                results=results,
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
            node_output = NodeOutput[FolderAnalyzerNodeOutputData](data=output_data)

            # Create execution result
            result = FolderAnalyzerNodeExecutionResult(
                node_identifier=node_id,
                status=ExecutionStatusEnum.COMPLETED if all_succeeded else ExecutionStatusEnum.FAILED,
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

    def _extract_operations(
        self,
        node_input: FolderAnalyzerNodeInput,
        settings: FolderAnalyzerSettings,
        execution_context: ExecutionContext,
    ) -> list[FolderAnalysisOperation]:
        """Extract folder analysis operations from various sources."""
        operations: list[FolderAnalysisOperation] = []

        # Extract operations from operations_template if provided
        if hasattr(settings, "operations_template") and settings.operations_template is not None:
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
                                operations.append(FolderAnalysisOperation(**op))
                            elif isinstance(op, FolderAnalysisOperation):
                                operations.append(op)
                            else:
                                logger.warning(f"Unexpected operation type in list: {type(op)}")
                    # Handle single operation as dict
                    elif isinstance(template_result, dict):
                        operations = [FolderAnalysisOperation(**template_result)]
                    # Handle JSON string
                    elif isinstance(template_result, str):
                        try:
                            # Try parsing as JSON
                            parsed_ops = json.loads(template_result)
                            if isinstance(parsed_ops, list):
                                operations = [FolderAnalysisOperation(**op) for op in parsed_ops]
                            elif isinstance(parsed_ops, dict):
                                operations = [FolderAnalysisOperation(**parsed_ops)]
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
                        operations = [FolderAnalysisOperation(**op) for op in ops_data["operations"]]
                    elif isinstance(ops_data, list):
                        operations = [FolderAnalysisOperation(**op) for op in ops_data]
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON in operations: {e}")
            elif hasattr(node_input, "operations") and node_input.operations:
                operations = node_input.operations
            elif hasattr(settings, "operations") and settings.operations:
                operations = settings.operations

        return operations

    async def _execute_operations(
        self,
        base_directory: str,
        operations: list[FolderAnalysisOperation],
        settings: FolderAnalyzerSettings,
    ) -> tuple[list[FolderAnalysisOperationResult], int, int, list[str]]:
        """
        Execute all file operations and return results.

        Returns:
            tuple containing:
            - list of OperationResult objects
            - count of successful operations
            - count of failed operations
            - list of error messages
        """

        # Process all operations
        results = [FolderAnalysisOperationResult]
        successful_operations = 0
        failed_operations = 0
        errors = []
        total_files = 0
        total_directories = 0
        total_size = 0
        file_types = {}
        total_words_read = 0

        # Parse gitignore if needed
        exclude_patterns = []
        if settings.respect_gitignore:
            exclude_patterns = self._parse_gitignore(Path(base_directory))

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
                        FolderAnalysisOperationResult(
                            type=operation.type, path=operation.path, success=False, error=error_msg
                        )
                    )
                    errors.append(error_msg)
                    failed_operations += 1
                    if settings.fail_fast:
                        break
                    continue

                # Process operation based on type
                if operation.operation_type == "analyze_folder":
                    result = self._process_analyze_folder_operation(
                        base_directory=base_directory,
                        operation=operation,
                        exclude_patterns=exclude_patterns,
                        total_words_read=total_words_read,
                    )
                elif operation.operation_type == "analyze_file":
                    result = self._process_analyze_file_operation(
                        base_directory=base_directory, operation=operation, total_words_read=total_words_read
                    )
                elif operation.operation_type == "find_files":
                    result = self._process_find_files_operation(base_directory=base_directory, operation=operation)
                elif operation.operation_type == "get_structure":
                    result = self._process_get_structure_operation(base_directory=base_directory, operation=operation)

                else:
                    result = FolderAnalysisOperationResult(
                        operation_type=operation.operation_type,
                        path=operation.path,
                        success=False,
                        error=f"Unsupported operation type: {operation.operation_type}",
                    )

                # Add result to list
                results.append(result)

                # Update counters
                if result.success:
                    successful_operations += 1
                    if result.total_files:
                        total_files += result.total_files
                    if result.total_directories:
                        total_directories += result.total_directories
                    if result.total_size:
                        total_size += result.total_size
                else:
                    failed_operations += 1
                    if result.error:
                        errors.append(result.error)
                    if settings.fail_fast:
                        break

            except Exception as e:
                # Handle exceptions for each operation
                error_msg = f"Error performing {operation.operation_type} on {operation.path}: {e}"
                results.append(
                    FolderAnalysisOperationResult(
                        operation_type=operation.operation_type,
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

        meta = {
            "total_files": total_files,
            "total_directories": total_directories,
            "total_size": total_size,
            "file_types": file_types,
            "total_words_read": total_words_read,
        }
        return results, successful_operations, failed_operations, errors, meta

    def _process_analyze_folder_operation(
        self,
        base_directory: Path,
        operation: FolderAnalysisOperation,
        exclude_patterns: list[str],
        total_words_read: int,
    ) -> FolderAnalysisOperationResult:
        """Process an analyze_folder operation"""
        # Convert path to Path object and resolve
        path = Path(base_directory) / operation.path

        # Verify path exists and is a directory
        if not path.exists():
            return FolderAnalysisOperationResult(
                operation_type="analyze_folder", path=str(path), success=False, error=f"Path does not exist: {path}"
            )
        elif not path.is_dir():
            return FolderAnalysisOperationResult(
                operation_type="analyze_folder", path=str(path), success=False, error=f"Path is not a directory: {path}"
            )

        # Analyze folder
        analysis, stats = self._analyze_folder(
            path=path,
            root_path=path,
            settings=self._operation_to_settings(operation, base_directory),
            exclude_patterns=exclude_patterns + operation.exclude_patterns,
            current_depth=0,
            total_words_read=total_words_read,
        )

        # Generate tree diagram if requested
        tree_diagram = None
        if operation.generate_tree_diagram:
            tree_diagram = self._generate_tree_diagram(
                path=path,
                settings=self._operation_to_settings(operation, base_directory),
                exclude_patterns=exclude_patterns + operation.exclude_patterns,
            )

        # Return result
        return FolderAnalysisOperationResult(
            operation_type="analyze_folder",
            path=str(path),
            success=True,
            analysis=analysis,
            tree_diagram=tree_diagram,
            total_files=stats["total_files"],
            total_directories=stats["total_dirs"],
            total_size=stats["total_size"],
        )

    def _process_analyze_file_operation(
        self, base_directory: Path, operation: FolderAnalysisOperation, total_words_read: int
    ) -> FolderAnalysisOperationResult:
        """Process an analyze_file operation"""
        # Convert path to Path object and resolve
        path = Path(base_directory) / operation.path

        # Verify path exists and is a file
        if not path.exists():
            return FolderAnalysisOperationResult(
                operation_type="analyze_file", path=str(path), success=False, error=f"Path does not exist: {path}"
            )
        elif not path.is_file():
            return FolderAnalysisOperationResult(
                operation_type="analyze_file", path=str(path), success=False, error=f"Path is not a file: {path}"
            )

        # Analyze file
        file_info = self._analyze_file(
            path=path,
            root_path=base_directory,
            settings=self._operation_to_settings(operation, base_directory),
            total_words_read=total_words_read,
            skip_content=not operation.read_content,
        )

        # Return result
        return FolderAnalysisOperationResult(
            operation_type="analyze_file",
            path=str(path),
            success=True,
            file_info=file_info,
            total_files=1,
            total_directories=0,
            total_size=file_info.metadata.size if file_info.metadata else 0,
        )

    def _process_find_files_operation(
        self, base_directory: Path, operation: FolderAnalysisOperation
    ) -> FolderAnalysisOperationResult:
        """Process a find_files operation"""
        # Convert path to Path object and resolve
        path = Path(base_directory) / operation.path

        # Verify path exists and is a directory
        if not path.exists():
            return FolderAnalysisOperationResult(
                operation_type="find_files", path=str(path), success=False, error=f"Path does not exist: {path}"
            )
        elif not path.is_dir():
            return FolderAnalysisOperationResult(
                operation_type="find_files", path=str(path), success=False, error=f"Path is not a directory: {path}"
            )

        # Find files matching patterns
        found_files = []
        exclude_patterns = operation.exclude_patterns

        # Recursive function to find files
        def find_files_recursive(current_path, current_depth=0):
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
                        found_files.append(str(item.relative_to(base_directory)))

                    # Process directories recursively
                    elif item.is_dir():
                        find_files_recursive(item, current_depth + 1)

            except (PermissionError, OSError) as e:
                logger.warning(f"Error accessing {current_path}: {e}")

        # Start recursive search
        find_files_recursive(path)

        # Return result
        return FolderAnalysisOperationResult(
            operation_type="find_files",
            path=str(path),
            success=True,
            files_found=found_files,
            total_files=len(found_files),
            total_directories=0,
        )

    def _process_get_structure_operation(
        self, base_directory: Path, operation: FolderAnalysisOperation
    ) -> FolderAnalysisOperationResult:
        """Process a get_structure operation - returns directory structure without file contents"""
        # Create a settings object with read_content set to False
        non_content_settings = self._operation_to_settings(operation, base_directory)
        non_content_settings.read_content = False
        non_content_settings.include_content_preview = False

        # Convert path to Path object and resolve
        path = Path(base_directory) / operation.path

        # Verify path exists
        if not path.exists():
            return FolderAnalysisOperationResult(
                operation_type="get_structure", path=str(path), success=False, error=f"Path does not exist: {path}"
            )

        # Generate tree diagram
        tree_diagram = self._generate_tree_diagram(
            path=path,
            settings=non_content_settings,
            exclude_patterns=operation.exclude_patterns,
        )

        # If it's a directory, get the structure
        if path.is_dir():
            analysis, stats = self._analyze_folder(
                path=path,
                root_path=path,
                settings=non_content_settings,
                exclude_patterns=operation.exclude_patterns,
                current_depth=0,
                total_words_read=0,
            )

            return FolderAnalysisOperationResult(
                operation_type="get_structure",
                path=str(path),
                success=True,
                analysis=analysis,
                tree_diagram=tree_diagram,
                total_files=stats["total_files"],
                total_directories=stats["total_dirs"],
                total_size=stats["total_size"],
            )
        # If it's a file, return file info
        elif path.is_file():
            file_info = self._analyze_file(
                path=path,
                root_path=base_directory,
                settings=non_content_settings,
                total_words_read=0,
                skip_content=True,
            )

            return FolderAnalysisOperationResult(
                operation_type="get_structure",
                path=str(path),
                success=True,
                file_info=file_info,
                total_files=1,
                total_directories=0,
                total_size=file_info.metadata.size if file_info.metadata else 0,
            )
        else:
            return FolderAnalysisOperationResult(
                operation_type="get_structure",
                path=str(path),
                success=False,
                error=f"Path is neither a file nor a directory: {path}",
            )

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
                logger.warning(f"Error parsing .gitignore file: {e}")

        return patterns

    def _should_exclude(self, path: Path, exclude_patterns: list[str], include_hidden: bool) -> bool:
        """Check if a path should be excluded based on patterns and hidden status."""
        # Check for hidden files/directories
        if not include_hidden and path.name.startswith("."):
            return True

        # Check exclude patterns
        for pattern in exclude_patterns:
            # Handle directory-only patterns ending with /
            if pattern.endswith("/") and path.is_dir():
                dir_pattern = pattern.rstrip("/")
                if fnmatch.fnmatch(path.name, dir_pattern):
                    return True
            # Regular glob pattern matching
            elif fnmatch.fnmatch(path.name, pattern):
                return True
            # Handle path-based patterns (like "dir/subdir/*.py")
            elif "/" in pattern:
                rel_path_str = str(path.relative_to(path.parent.parent))
                if fnmatch.fnmatch(rel_path_str, pattern):
                    return True

        return False

    def _analyze_folder(
        self,
        path: Path,
        root_path: Path,
        settings: FolderAnalyzerSettings,
        exclude_patterns: list[str],
        current_depth: int,
        total_words_read: int,
    ) -> tuple[DirectoryInfo, dict[str, Any]]:
        """
        Recursively analyze a folder structure with enhanced options.
        Returns DirectoryInfo and stats.
        """
        # Initialize stats
        stats = {
            "total_files": 0,
            "total_dirs": 0,
            "total_size": 0,
            "file_types": {},
            "errors": [],
        }

        # Check max depth
        if settings.max_depth is not None and current_depth > settings.max_depth:
            return DirectoryInfo(type="directory", name=path.name, path=str(path), truncated=True), stats

        # Format the path according to settings
        formatted_path = self._format_path(path, root_path, settings)

        result = DirectoryInfo(
            type="directory",
            name=path.name,
            path=formatted_path,
            children=[],
        )

        # Include stats if requested
        if settings.include_stats:
            try:
                stat = path.stat()
                result.size = stat.st_size
                result.created = datetime.fromtimestamp(stat.st_ctime).isoformat()
                result.modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                result.accessed = datetime.fromtimestamp(stat.st_atime).isoformat()
                result.permissions = filemode(stat.st_mode)
                stats["total_size"] += stat.st_size
            except (PermissionError, OSError) as e:
                error_msg = f"Failed to get stats for {path}: {e}"
                result.error = error_msg
                stats["errors"].append(error_msg)

        # Process children
        file_count = 0
        dir_count = 0

        try:
            for item in path.iterdir():
                # Check if item should be excluded
                if self._should_exclude(item, exclude_patterns, settings.include_hidden):
                    continue

                if item.is_dir():
                    dir_count += 1
                    stats["total_dirs"] += 1

                    # Recursively analyze subdirectory
                    child_result, child_stats = self._analyze_folder(
                        path=item,
                        root_path=root_path,
                        settings=settings,
                        exclude_patterns=exclude_patterns,
                        current_depth=current_depth + 1,
                        total_words_read=total_words_read,
                    )

                    # Merge stats
                    stats["total_files"] += child_stats["total_files"]
                    stats["total_dirs"] += child_stats["total_dirs"]
                    stats["total_size"] += child_stats["total_size"]

                    # Merge file types
                    for ext, count in child_stats["file_types"].items():
                        if ext in stats["file_types"]:
                            stats["file_types"][ext] += count
                        else:
                            stats["file_types"][ext] = count

                    # Merge errors
                    stats["errors"].extend(child_stats["errors"])
                    result.children.append(child_result)

                elif item.is_file():
                    file_count += 1
                    stats["total_files"] += 1

                    # Check if we've reached the word limit
                    if settings.max_total_words and total_words_read >= settings.max_total_words:
                        # Skip reading content if we've reached the total word limit
                        file_result = self._analyze_file(
                            item,
                            root_path,
                            settings,
                            total_words_read,
                            skip_content=True,
                        )
                    else:
                        # Analyze file with regular settings
                        file_result = self._analyze_file(item, root_path, settings, total_words_read)

                    # Update file type stats
                    ext = file_result.extension.lower()
                    if ext in stats["file_types"]:
                        stats["file_types"][ext] += 1
                    else:
                        stats["file_types"][ext] = 1

                    if file_result.metadata and file_result.metadata.size:
                        stats["total_size"] += file_result.metadata.size

                    if file_result.error:
                        stats["errors"].append(file_result.error)

                    result.children.append(file_result)

            # Add counts to result
            result.file_count = file_count
            result.dir_count = dir_count

            return result, stats

        except (PermissionError, OSError) as e:
            error_msg = f"Failed to read directory {path}: {e}"
            result.error = error_msg
            stats["errors"].append(error_msg)
            return result, stats

    def _analyze_file(
        self,
        path: Path,
        root_path: Path,
        settings: FolderAnalyzerSettings,
        total_words_read: int,
        skip_content: bool = False,
    ) -> FileInfo:
        """Analyze a single file with enhanced options."""
        # Format the path according to settings
        formatted_path = self._format_path(path, root_path, settings)

        result = FileInfo(
            type="file",
            name=path.name,
            path=formatted_path,
            extension=path.suffix.lower(),
        )

        # Include stats if requested
        if settings.include_stats:
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
        if skip_content:
            return result

        # Analyze content if requested

        # Use unix cmds to get wordcount irrespective of the content_read_mode
        result.word_count = self.word_count(path)

        should_read_content = settings.include_content_preview or settings.read_content
        if should_read_content:
            if settings.content_read_mode == "structure" and path.suffix.lower() == ".py":
                from .helpers.python_extractor import PythonStructureExtractor

                try:
                    # Use Python's built-in ast module
                    extractor = PythonStructureExtractor(path)
                    structure = extractor.extract(detail_level=settings.content_structure_detail_level)

                    formatted_structure = [f"{key}: {value}" for key, value in structure.items()]
                    result.content_structure = "\n\n".join(formatted_structure)

                    word_count = len(result.content_structure.split())
                    total_words_read += word_count

                except Exception as e:
                    # Fallback to regular content processing
                    result.error = f"Failed to extract structure: {e}"

            elif settings.content_read_mode == "smart_chunks" and settings.use_langchain_splitter:
                # TODO_FUTURE: Not functional
                from .helpers.helper_fns import optimize_for_llm_context

                try:
                    result.content = optimize_for_llm_context(path, settings)
                    word_count = len(result.content.split())
                    total_words_read += word_count
                except Exception as e:
                    result.error = f"Smart chunking failed: {e}"

        # Fallback to original method for other modes or when other methods fail
        if should_read_content and (settings.content_read_mode == "full" or not result.content_structure):
            # Check file size limit
            file_size = result.metadata.size if result.metadata else 0
            if settings.max_file_size is None or file_size <= settings.max_file_size:
                mime_type = None
                is_text = None
                try:
                    # Get mime type
                    mime_type, _ = mimetypes.guess_type(str(path))

                    # For text files, try to determine encoding and sample content
                    is_likely_text = mime_type and (
                        mime_type.startswith("text/")
                        or mime_type
                        in [
                            "application/json",
                            "application/xml",
                            "application/javascript",
                            "application/x-python",
                        ]
                    )

                    if is_likely_text:
                        try:
                            with open(path, encoding="utf-8") as f:
                                if settings.read_content:
                                    # Read full content
                                    content = f.read()

                                    # Apply word limit per file if specified
                                    if settings.max_words_per_file:
                                        words = content.split()
                                        if len(words) > settings.max_words_per_file:
                                            content = " ".join(words[: settings.max_words_per_file])
                                            content += f"\n... [truncated after {settings.max_words_per_file} words]"

                                    # Track total words read
                                    word_count = len(content.split())
                                    total_words_read += word_count

                                    # Add content to result
                                    result.content = content
                                    # result.word_count = word_count

                                elif settings.include_content_preview:
                                    # Just read first few lines for preview
                                    content_preview = "".join(f.readline() for _ in range(5))
                                    result.content_preview = content_preview

                                # Generate a summary if requested
                                if settings.generate_file_summary:
                                    summary = self._generate_file_summary(
                                        path, result.content or result.content_preview
                                    )
                                    result.summary = summary

                                is_text = True
                        except UnicodeDecodeError:
                            is_text = False
                    else:
                        is_text = False
                except Exception as e:
                    result.error = f"Error analyzing content: {e}"

                result.mime_type = mime_type or "application/octet-stream"
                result.is_text = is_text

        return result

    def word_count(self, filepath):
        import subprocess

        result = subprocess.run(["wc", "-w", filepath], capture_output=True, text=True)
        return int(result.stdout.split()[0])

    def resolve_dad_template_path(
        self,
        node_id: NodeID,
        node_input: FolderAnalyzerNodeInput,
        execution_context: ExecutionContext,
        settings: FolderAnalyzerSettings,
    ) -> tuple[list[str], Path]:
        """Format path with variables."""
        variables = {}
        dad_dynamic_variables = execution_context.get_dad_dynamic_variables()

        _path = node_input.path if hasattr(node_input, "path") and node_input.path else settings.path

        # Resolve working directory
        path = DADTemplateEngine.render_dad_template(
            template=_path,
            variables=variables,
            dad_dynamic_variables=dad_dynamic_variables,
            run_env_params=execution_context.run_context.run_env_params,
            node_execution_results=None,
        )
        return Path(path).expanduser().resolve()

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
            return f"Text document: {first_line[:50]}{'...' if len(first_line) > 50 else ''}\nTotal lines: {len(lines)}"

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

    def _format_path(self, path: Path, root_path: Path, settings: FolderAnalyzerSettings) -> str:
        """Format a path according to the specified settings."""
        if settings.use_relative_paths:
            try:
                # Get the relative path from the root
                rel_path = path.relative_to(root_path)

                # Handle the root directory case
                if str(rel_path) == ".":
                    if settings.include_root_in_path:
                        return path.name
                    else:
                        return "."

                # For other paths, add the root name if requested
                if settings.include_root_in_path:
                    return str(Path(root_path.name) / rel_path)
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
        settings: FolderAnalyzerSettings,
        exclude_patterns: list[str],
    ) -> str:
        """Generate a human-readable ASCII tree diagram of the directory structure."""
        tree_lines = []
        max_depth = settings.tree_diagram_max_depth or settings.max_depth

        # Store the root directory name
        root_name = path.name or str(path)
        tree_lines.append(root_name)

        # Process the directory structure
        self._build_tree_diagram(
            path=path,
            prefix="",
            tree_lines=tree_lines,
            exclude_patterns=exclude_patterns,
            settings=settings,
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
        settings: FolderAnalyzerSettings,
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
                if self._should_exclude(item, exclude_patterns, settings.include_hidden):
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
                        settings=settings,
                        current_depth=current_depth + 1,
                        max_depth=max_depth,
                    )
                # Skip files if requested
                elif not item.is_file() or not settings.tree_diagram_include_files:
                    continue

        except (PermissionError, OSError) as e:
            # Handle access errors
            tree_lines.append(f"{prefix}├── [Error: {e}]")
