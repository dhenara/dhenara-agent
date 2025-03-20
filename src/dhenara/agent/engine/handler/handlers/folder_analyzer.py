# dhenara/agent/engine/handlers/folder_analyzer.py
import fnmatch
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any

from dhenara.agent.dsl.base import ExecutableNodeDefinition, ExecutionContext
from dhenara.agent.engine.handler import NodeHandler
from dhenara.agent.types import FlowNodeTypeEnum, FolderAnalyzerSettings, NodeInput
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)


class FolderAnalyzerHandler(NodeHandler):
    """Handler for analyzing folder structure."""

    def __init__(self):
        super().__init__(identifier="folder_analyzer_handler")

    async def handle(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        resource_config: ResourceConfig,
    ) -> Any:
        """Analyze folder structure as defined in the flow node."""
        try:
            if node_definition.type == FlowNodeTypeEnum.folder_analyzer:
                settings = node_definition.folder_analyzer_settings
            elif node_definition.type == FlowNodeTypeEnum.git_repo_analyzer:
                settings = node_definition.git_repo_analyzer_settings
            else:
                raise ValueError(f"Illegal node type {node_definition.type} for analyzer handler")

            # Validate folder analyzer settings
            if not settings:
                raise ValueError("analyzer_settings is required for analyzer nodes")

            # Resolve path with variable interpolation
            path = settings.get_formatted_path(run_env_params=execution_context.run_env_params)
            path = Path(path).expanduser().resolve()

            # Check if path exists and is a directory
            if not path.exists():
                return {"error": f"Path does not exist: {path}", "success": False}

            if not path.is_dir():
                return {"error": f"Path is not a directory: {path}", "success": False}

            # Analyze folder structure
            analysis = self._analyze_folder(path=path, settings=settings, current_depth=0)

            return {"success": True, "path": str(path), "analysis": analysis}

        except Exception as e:
            logger.exception(f"Error analyzing folder: {e}")
            raise DhenaraAPIError(f"Folder analysis failed: {e!s}")

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

    def _analyze_folder(self, path: Path, settings: FolderAnalyzerSettings, current_depth: int) -> dict[str, Any]:
        """Recursively analyze a folder structure."""
        # Check max depth
        if settings.max_depth is not None and current_depth > settings.max_depth:
            return {"type": "directory", "name": path.name, "truncated": True}

        result = {
            "type": "directory",
            "name": path.name,
            "path": str(path),
            "children": [],
        }

        # Include stats if requested
        if settings.include_stats:
            try:
                stat = path.stat()
                result.update(
                    {
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )
            except (PermissionError, OSError) as e:
                result["error"] = f"Failed to get stats: {e!s}"

        # Count files and directories
        file_count = 0
        dir_count = 0

        try:
            # Process children
            for item in path.iterdir():
                # Check if item should be excluded
                if self._should_exclude(item, settings.exclude_patterns, settings.include_hidden):
                    continue

                if item.is_dir():
                    dir_count += 1
                    # Recursively analyze subdirectory
                    child_result = self._analyze_folder(path=item, settings=settings, current_depth=current_depth + 1)
                    result["children"].append(child_result)

                elif item.is_file():
                    file_count += 1
                    # Analyze file
                    file_result = self._analyze_file(item, settings)
                    result["children"].append(file_result)

            # Add counts to result
            result["file_count"] = file_count
            result["dir_count"] = dir_count

            return result

        except (PermissionError, OSError) as e:
            result["error"] = f"Failed to read directory: {e!s}"
            return result

    def _analyze_file(self, path: Path, settings: FolderAnalyzerSettings) -> dict[str, Any]:
        """Analyze a single file."""
        result = {
            "type": "file",
            "name": path.name,
            "path": str(path),
            "extension": path.suffix.lower(),
        }

        # Include stats if requested
        if settings.include_stats:
            try:
                stat = path.stat()
                result.update(
                    {
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )
            except (PermissionError, OSError) as e:
                result["error"] = f"Failed to get stats: {e!s}"

        # Analyze content if requested
        if settings.include_content:
            # Check file size limit
            file_size = result.get("size", 0)
            if settings.max_file_size is None or file_size <= settings.max_file_size:
                try:
                    # Get mime type
                    mime_type, encoding = mimetypes.guess_type(str(path))
                    result["mime_type"] = mime_type or "application/octet-stream"

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
                                result["content_preview"] = content_preview
                                result["is_text"] = True
                        except UnicodeDecodeError:
                            result["is_text"] = False
                    else:
                        result["is_text"] = False

                except Exception as e:
                    result["content_error"] = str(e)

        return result
