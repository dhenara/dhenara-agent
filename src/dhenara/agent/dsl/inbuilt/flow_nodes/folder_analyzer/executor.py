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
from dhenara.agent.dsl.flow import FlowNodeExecutor
from dhenara.ai.types.resource import ResourceConfig

from .input import FolderAnalyzerNodeInput
from .output import DirectoryInfo, FileInfo, FolderAnalyzerNodeOutcome, FolderAnalyzerNodeOutputData
from .settings import FolderAnalyzerSettings

logger = logging.getLogger(__name__)


class FolderAnalyzerNodeExecutor(FlowNodeExecutor):
    """Executor for Folder Analyzer Node."""

    input_model = FolderAnalyzerNodeInput
    setting_model = FolderAnalyzerSettings

    def __init__(self):
        super().__init__(identifier="foldera_analyzer_executor")

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
            if not isinstance(settings, FolderAnalyzerSettings):
                raise ValueError(f"Invalid settings type: {type(settings)}")

            # Override path if provided in input
            path = self.get_formatted_path(
                node_id=node_id,
                node_input=node_input,
                execution_context=execution_context,
                settings=settings,
            )

            # Convert path to Path object and resolve
            path = Path(path).expanduser().resolve()

            # Verify path exists and is a directory
            if not path.exists():
                output_data = FolderAnalyzerNodeOutputData(
                    success=False, path=str(path), error=f"Path does not exist: {path}"
                )
                outcome = FolderAnalyzerNodeOutcome(success=False, errors=[f"Path does not exist: {path}"])
            elif not path.is_dir():
                output_data = FolderAnalyzerNodeOutputData(
                    success=False, path=str(path), error=f"Path is not a directory: {path}"
                )
                outcome = FolderAnalyzerNodeOutcome(success=False, errors=[f"Path is not a directory: {path}"])
            else:
                # Merge exclude patterns from settings and input
                exclude_patterns = list(settings.exclude_patterns)
                if hasattr(node_input, "exclude_patterns") and node_input.exclude_patterns:
                    exclude_patterns.extend(node_input.exclude_patterns)

                # Analyze folder
                analysis, stats = self._analyze_folder(
                    path=path, settings=settings, exclude_patterns=exclude_patterns, current_depth=0
                )

                output_data = FolderAnalyzerNodeOutputData(success=True, path=str(path), analysis=analysis)

                outcome = FolderAnalyzerNodeOutcome(
                    success=True,
                    total_files=stats["total_files"],
                    total_directories=stats["total_dirs"],
                    total_size=stats["total_size"],
                    file_types=stats["file_types"],
                    errors=stats["errors"],
                )

            # Create node output
            node_output = NodeOutput[FolderAnalyzerNodeOutputData](data=output_data)

            # Create execution result
            result = NodeExecutionResult(
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

            return output_data

        except Exception as e:
            logger.exception(f"Folder analyzer execution error: {e}")
            self.set_node_execution_failed(
                node_definition=node_definition,
                execution_context=execution_context,
                message=f"Folder analysis failed: {e}",
            )
            return None

    def _should_exclude(self, path: Path, exclude_patterns: list[str], include_hidden: bool) -> bool:
        """Check if a path should be excluded based on patterns and hidden status."""
        # Check for hidden files/directories
        if not include_hidden and path.name.startswith("."):
            return True

        # Check exclude patterns
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(path.name, pattern):
                return True

        return False

    def _analyze_folder(
        self, path: Path, settings: FolderAnalyzerSettings, exclude_patterns: list[str], current_depth: int
    ) -> tuple[DirectoryInfo, dict[str, Any]]:
        """
        Recursively analyze a folder structure.
        Returns DirectoryInfo and stats.
        """
        # Initialize stats
        stats = {"total_files": 0, "total_dirs": 0, "total_size": 0, "file_types": {}, "errors": []}

        # Check max depth
        if settings.max_depth is not None and current_depth > settings.max_depth:
            return DirectoryInfo(type="directory", name=path.name, path=str(path), truncated=True), stats

        result = DirectoryInfo(
            type="directory",
            name=path.name,
            path=str(path),
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

        # Count files and directories
        file_count = 0
        dir_count = 0

        try:
            # Process children
            for item in path.iterdir():
                # Check if item should be excluded
                if self._should_exclude(item, exclude_patterns, settings.include_hidden):
                    continue

                if item.is_dir():
                    dir_count += 1
                    stats["total_dirs"] += 1

                    # Recursively analyze subdirectory
                    child_result, child_stats = self._analyze_folder(
                        path=item, settings=settings, exclude_patterns=exclude_patterns, current_depth=current_depth + 1
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

                    # Analyze file
                    file_result = self._analyze_file(item, settings)

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

    def _analyze_file(self, path: Path, settings: FolderAnalyzerSettings) -> FileInfo:
        """Analyze a single file."""
        result = FileInfo(
            type="file",
            name=path.name,
            path=str(path),
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

        # Analyze content if requested
        if settings.include_content:
            # Check file size limit
            file_size = result.size or 0
            if settings.max_file_size is None or file_size <= settings.max_file_size:
                try:
                    # Get mime type
                    mime_type, _ = mimetypes.guess_type(str(path))
                    result.mime_type = mime_type or "application/octet-stream"

                    # For text files, try to determine encoding and sample content
                    if mime_type and (
                        mime_type.startswith("text/")
                        or mime_type
                        in [
                            "application/json",
                            "application/xml",
                            "application/javascript",
                        ]
                    ):
                        try:
                            with open(path, encoding="utf-8") as f:
                                # Just read first few lines for preview
                                content_preview = "".join(f.readline() for _ in range(5))
                                result.content_preview = content_preview
                                result.is_text = True
                        except UnicodeDecodeError:
                            result.is_text = False
                    else:
                        result.is_text = False
                except Exception as e:
                    result.error = f"Error analyzing content: {e}"

        return result

    def get_formatted_path(
        self,
        node_id: NodeID,
        node_input: FolderAnalyzerNodeInput,
        execution_context: ExecutionContext,
        settings: FolderAnalyzerSettings,
    ) -> tuple[list[str], Path]:
        """Format path with variables."""
        variables = {}
        dad_dynamic_variables = {
            "node_id": node_id,
        }

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
