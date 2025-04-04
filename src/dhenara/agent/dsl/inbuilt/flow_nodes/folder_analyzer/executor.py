import fnmatch
import logging
import mimetypes
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
from dhenara.agent.dsl.flow import FlowNodeExecutor, FlowNodeTypeEnum
from dhenara.agent.observability.tracing import trace_node
from dhenara.agent.observability.tracing.data import TracingDataCategory, add_trace_attribute
from dhenara.ai.types.resource import ResourceConfig

from .input import FolderAnalyzerNodeInput
from .output import (
    DirectoryInfo,
    FileInfo,
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


class FolderAnalyzerNodeExecutor(FlowNodeExecutor):
    """Executor for Folder Analyzer Node."""

    input_model = FolderAnalyzerNodeInput
    setting_model = FolderAnalyzerSettings
    _tracing_profile = folder_analyzer_node_tracing_profile

    def __init__(self):
        super().__init__(identifier="folder_analyzer_executor")
        self._total_words_read = 0

    def get_result_class(self):
        return FolderAnalyzerNodeExecutionResult

    @trace_node(FlowNodeTypeEnum.folder_analyzer.value)
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        node_input: NodeInput,
        resource_config: ResourceConfig,
    ) -> FolderAnalyzerNodeExecutionResult | None:
        try:
            # Get settings from node definition or input override
            settings = node_definition.select_settings(node_input=node_input)
            if not isinstance(settings, FolderAnalyzerSettings):
                raise ValueError(f"Invalid settings type: {type(settings)}")

            # Override path if provided in input
            path = self.resolve_dad_template_path(
                node_id=node_id,
                node_input=node_input,
                execution_context=execution_context,
                settings=settings,
            )

            # Convert path to Path object and resolve
            path = Path(path).expanduser().resolve()

            # Store the root path for relative path calculations
            root_path = path

            # Add trace attributes for better visibility
            add_trace_attribute("path", str(path), TracingDataCategory.primary)
            add_trace_attribute("max_depth", settings.max_depth, TracingDataCategory.secondary)
            add_trace_attribute("include_hidden", settings.include_hidden, TracingDataCategory.secondary)
            add_trace_attribute("include_stats", settings.include_stats, TracingDataCategory.secondary)
            add_trace_attribute(
                "include_content_preview",
                settings.include_content_preview,
                TracingDataCategory.secondary,
            )
            add_trace_attribute("read_content", settings.read_content, TracingDataCategory.secondary)
            add_trace_attribute("respect_gitignore", settings.respect_gitignore, TracingDataCategory.secondary)
            add_trace_attribute("use_relative_paths", settings.use_relative_paths, TracingDataCategory.secondary)
            add_trace_attribute("include_root_in_path", settings.include_root_in_path, TracingDataCategory.secondary)
            add_trace_attribute("generate_tree_diagram", settings.generate_tree_diagram, TracingDataCategory.secondary)

            # Reset total words counter
            self._total_words_read = 0

            # Verify path exists and is a directory
            if not path.exists():
                add_trace_attribute("error", f"Path does not exist: {path}", TracingDataCategory.primary)
                output_data = FolderAnalyzerNodeOutputData(
                    success=False, path=str(path), error=f"Path does not exist: {path}"
                )
                outcome = FolderAnalyzerNodeOutcome(success=False, errors=[f"Path does not exist: {path}"])
            elif not path.is_dir():
                add_trace_attribute("error", f"Path is not a directory: {path}", TracingDataCategory.primary)
                output_data = FolderAnalyzerNodeOutputData(
                    success=False, path=str(path), error=f"Path is not a directory: {path}"
                )
                outcome = FolderAnalyzerNodeOutcome(success=False, errors=[f"Path is not a directory: {path}"])
            else:
                # Merge exclude patterns from settings and input
                exclude_patterns = list(settings.exclude_patterns)
                if hasattr(node_input, "exclude_patterns") and node_input.exclude_patterns:
                    exclude_patterns.extend(node_input.exclude_patterns)

                # Parse gitignore if needed
                gitignore_patterns = []
                if settings.respect_gitignore:
                    gitignore_patterns = self._parse_gitignore(path)
                    exclude_patterns.extend(gitignore_patterns)

                # Analyze folder
                analysis, stats = self._analyze_folder(
                    path=path,
                    root_path=root_path,
                    settings=settings,
                    exclude_patterns=exclude_patterns,
                    current_depth=0,
                )

                # Generate tree diagram if requested
                if settings.generate_tree_diagram:
                    tree_diagram = self._generate_tree_diagram(
                        path=path,
                        settings=settings,
                        exclude_patterns=exclude_patterns,
                    )

                outcome = FolderAnalyzerNodeOutcome(
                    success=True,
                    tree_diagram=tree_diagram,
                    analysis=analysis,
                    total_files=stats["total_files"],
                    total_directories=stats["total_dirs"],
                    total_size=stats["total_size"],
                    file_types=stats["file_types"],
                    errors=stats["errors"],
                    gitignore_patterns=gitignore_patterns if settings.respect_gitignore else None,
                    total_words_read=self._total_words_read if settings.read_content else None,
                )

                # Avoid duplicated large analysis data on output and outcome
                analysis_for_output = (
                    None
                    if node_definition.record_settings.outcome and node_definition.record_settings.outcome.enabled
                    else analysis
                )

                output_data = FolderAnalyzerNodeOutputData(
                    success=True,
                    path=str(path),
                    analysis=analysis_for_output,
                )

            # Create node output
            node_output = NodeOutput[FolderAnalyzerNodeOutputData](data=output_data)

            # After analysis is complete
            if "analysis" in locals() and analysis:
                add_trace_attribute(
                    "stats_summary",
                    {
                        "total_files": stats["total_files"],
                        "total_dirs": stats["total_dirs"],
                        "total_size": stats["total_size"],
                        "file_types_count": len(stats["file_types"]),
                        "errors_count": len(stats["errors"]),
                        "total_words_read": self._total_words_read if settings.read_content else 0,
                    },
                    TracingDataCategory.primary,
                )

            # Create execution result
            result = FolderAnalyzerNodeExecutionResult(
                node_identifier=node_id,
                status=ExecutionStatusEnum.COMPLETED if output_data.success else ExecutionStatusEnum.FAILED,
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
            logger.exception(f"Folder analyzer execution error: {e}")
            return self.set_node_execution_failed(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
                message=f"Folder analysis failed: {e}",
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
    ) -> tuple[DirectoryInfo, dict[str, Any]]:
        """
        Recursively analyze a folder structure with enhanced options.
        Returns DirectoryInfo and stats.
        """
        # Initialize stats
        stats = {"total_files": 0, "total_dirs": 0, "total_size": 0, "file_types": {}, "errors": []}

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
                    if settings.max_total_words and self._total_words_read >= settings.max_total_words:
                        # Skip reading content if we've reached the total word limit
                        file_result = self._analyze_file(item, root_path, settings, skip_content=True)
                    else:
                        # Analyze file with regular settings
                        file_result = self._analyze_file(item, root_path, settings)

                    # Update file type stats
                    ext = file_result.extension.lower()
                    if ext in stats["file_types"]:
                        stats["file_types"][ext] += 1
                    else:
                        stats["file_types"][ext] = 1

                    if file_result.size:
                        stats["total_size"] += file_result.size

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
                result.size = stat.st_size
                result.created = datetime.fromtimestamp(stat.st_ctime).isoformat()
                result.modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except (PermissionError, OSError) as e:
                result.error = f"Failed to get stats: {e}"

        # Skip content analysis if requested
        if skip_content:
            return result

        # Analyze content if requested
        should_read_content = settings.include_content_preview or settings.read_content
        if should_read_content:
            # Check file size limit
            file_size = result.size or 0
            if settings.max_file_size is None or file_size <= settings.max_file_size:
                try:
                    # Get mime type
                    mime_type, _ = mimetypes.guess_type(str(path))
                    result.mime_type = mime_type or "application/octet-stream"

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
                                    self._total_words_read += word_count

                                    # Add content to result
                                    result.content = content
                                    result.word_count = word_count

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

                                result.is_text = True
                        except UnicodeDecodeError:
                            result.is_text = False
                    else:
                        result.is_text = False
                except Exception as e:
                    result.error = f"Error analyzing content: {e}"

        return result

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
            mode="standard",
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
