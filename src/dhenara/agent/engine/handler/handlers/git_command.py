# Enhanced CommandHandler for Git operations
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from dhenara.agent.engine.handler import NodeHandler
from dhenara.agent.engine.types import FlowContext
from dhenara.agent.types import FlowNode, FlowNodeInput, FlowNodeOutput
from dhenara.agent.utils.git import GitBase
from dhenara.ai.types.resource import ResourceConfig

logger = logging.getLogger(__name__)


# TODO: Plug this in: Currently not used
class GitCommandHandler(NodeHandler):
    """Handler for Git command operations"""

    def __init__(self):
        super().__init__(identifier="git_command_handler")

    async def handle(
        self,
        flow_node: FlowNode,
        flow_node_input: FlowNodeInput,
        flow_context: FlowContext,
        resource_config: ResourceConfig,
    ) -> Any:
        # Extract command and parameters from input
        command_input = flow_node_input.content.get_content()

        try:
            # Parse the command input (expected JSON format)
            command_data = json.loads(command_input)
            git_operation = command_data.get("operation")
            params = command_data.get("params", {})

            # Get repository path
            repo_path = params.get("repo_path", ".")

            # Create GitBase instance
            git = GitBase(repo_path)

            # Execute the appropriate Git operation
            result = await self._execute_git_operation(git, git_operation, params)

            # Create node output
            return FlowNodeOutput(data={"success": True, "operation": git_operation, "result": result})
        except Exception as e:
            logger.exception(f"Git command execution failed: {e}")
            return FlowNodeOutput(data={"success": False, "error": str(e)})

    async def _execute_git_operation(self, git: GitBase, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the specified Git operation with the given parameters"""
        if operation == "clone":
            url = params.get("url")
            branch = params.get("branch")
            depth = params.get("depth")

            # Run Git clone as a subprocess
            cmd = ["git", "clone", url]
            if branch:
                cmd.extend(["--branch", branch])
            if depth:
                cmd.extend(["--depth", str(depth)])
            if "target_dir" in params:
                cmd.append(params["target_dir"])

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            return {
                "returncode": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "success": process.returncode == 0,
            }

        elif operation == "init":
            result = git._git_init()
            return {"success": result}

        elif operation == "add":
            paths = params.get("paths", [])
            result = git.add(paths)
            return {"success": result}

        elif operation == "commit":
            message = params.get("message", "Commit changes")
            result = git.commit(message)
            return {"success": result}

        elif operation == "checkout":
            branch = params.get("branch")
            create = params.get("create", False)
            result = git.checkout(branch, create)
            return {"success": result}

        elif operation == "list_files":
            pattern = params.get("pattern", "**/*")
            directory = Path(git.repo_path)
            files = [str(p.relative_to(directory)) for p in directory.glob(pattern) if p.is_file()]
            return {"files": files}

        elif operation == "create_file":
            file_path = params.get("file_path")
            content = params.get("content", "")

            full_path = Path(git.repo_path) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w") as f:  # noqa: ASYNC230: TODO_FUTURE
                f.write(content)

            return {"success": True, "file_path": file_path}

        else:
            raise ValueError(f"Unsupported Git operation: {operation}")
