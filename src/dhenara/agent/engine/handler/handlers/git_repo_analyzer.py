# dhenara/agent/engine/handlers/git_repo_analyzer.py
import logging
from pathlib import Path
from typing import Any

from dhenara.agent.engine.types import FlowContext
from dhenara.agent.types import FlowNode, FlowNodeInput, GitRepoAnalyzerSettings
from dhenara.agent.utils.git import GitBase
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError

from .folder_analyzer import FolderAnalyzerHandler

logger = logging.getLogger(__name__)


class GitRepoAnalyzerHandler(FolderAnalyzerHandler):
    """Handler for analyzing git repositories."""

    def __init__(self):
        super().__init__()
        self.identifier = "git_repo_analyzer_handler"  # Overrride after inint as this is child of FolderAnalyzerHandler

    async def handle(
        self,
        flow_node: FlowNode,
        flow_node_input: FlowNodeInput,
        flow_context: FlowContext,
        resource_config: ResourceConfig,
    ) -> Any:
        """Analyze git repository as defined in the flow node."""
        try:
            # Validate git repo analyzer settings
            if not flow_node.git_repo_analyzer_settings:
                raise ValueError("git_repo_analyzer_settings is required for git_repo_analyzer nodes")

            # If git_repo_analyzer_settings is a dict, convert it to a GitRepoAnalyzerSettings object
            if isinstance(flow_node.git_repo_analyzer_settings, dict):
                settings = GitRepoAnalyzerSettings(**flow_node.git_repo_analyzer_settings)
            else:
                settings = flow_node.git_repo_analyzer_settings

            # Resolve path with variable interpolation
            path = settings.get_formatted_path(run_env_params=flow_context.run_env_params)
            path = Path(path).expanduser().resolve()

            # Check if path exists and is a directory
            if not path.exists():
                return {"error": f"Path does not exist: {path}", "success": False}

            if not path.is_dir():
                return {"error": f"Path is not a directory: {path}", "success": False}

            # Check if this is a git repository
            git_dir = path / ".git"
            if not git_dir.exists() or not git_dir.is_dir():
                return {
                    "error": f"Path is not a git repository: {path}",
                    "success": False,
                }

            # First, do the basic folder analysis
            folder_analysis = await super().handle(flow_node, flow_node_input, flow_context, resource_config)

            # Then add git-specific information
            git_analysis = self._analyze_git_repo(path, settings)

            # Combine the results
            result = {
                "success": True,
                "path": str(path),
                "folder_analysis": folder_analysis.get("analysis", {}),
                "git_analysis": git_analysis,
            }

            return result

        except Exception as e:
            logger.exception(f"Error analyzing git repository: {e}")
            raise DhenaraAPIError(f"Git repository analysis failed: {e!s}")

    def _analyze_git_repo(self, path: Path, settings: GitRepoAnalyzerSettings) -> dict[str, Any]:
        """Analyze a git repository using the provided RepoAnalyzer."""
        # Use the provided RepoAnalyzer class
        from dhenara.agent.utils.git import GitRepoAnalyzer

        repo_analyzer = GitRepoAnalyzer(path)
        analysis = repo_analyzer.analyze_structure()

        # If we have additional git settings, enhance the analysis
        git_base = GitBase(path)

        # Add git-specific information if requested
        if settings.include_git_history:
            try:
                commits = git_base.get_logs(format_str="%h|%ad|%an|%s", date_format="iso")
                if settings.max_commits and len(commits) > settings.max_commits:
                    commits = commits[: settings.max_commits]

                analysis["git_history"] = commits
            except Exception as e:
                logger.warning(f"Failed to get git history: {e}")
                analysis["git_history_error"] = str(e)

        if settings.include_branch_info:
            try:
                branches = git_base.list_branches()
                current_branch = git_base.get_current_branch()

                analysis["git_branches"] = branches
                analysis["git_current_branch"] = current_branch

                # If specific branches were requested, get their info
                if settings.branches:
                    branch_info = {}
                    for branch in settings.branches:
                        if branch in branches:
                            # Get the latest commit on this branch
                            commits = git_base.get_logs(branch=branch, format_str="%h|%ad|%s", date_format="iso")
                            if commits:
                                branch_info[branch] = commits[0]
                            else:
                                branch_info[branch] = None

                    analysis["git_branch_info"] = branch_info
            except Exception as e:
                logger.warning(f"Failed to get branch information: {e}")
                analysis["git_branch_error"] = str(e)

        return analysis
