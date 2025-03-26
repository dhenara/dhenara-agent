import logging
from datetime import datetime
from pathlib import Path

from dhenara.agent.utils.git import GitBase

logger = logging.getLogger(__name__)


class RunOutcomeRepository(GitBase):
    """Manages git repository for agent run outcomes with branch-based organization."""

    def __init__(self, outcome_dir: Path):
        """Initialize the outcome repository.

        Args:
            outcome_dir: Directory for storing run outcomes
        """
        super().__init__(repo_path=outcome_dir)
        self.outcome_dir = outcome_dir
        self.base_branch = "main"
        self.init_repo(
            readme_content="# Agent Execution Outputs\n\nThis repository contains outcomes from agent executions.\n",
            commit=True,
        )

    def create_run_branch(self, branch_name: str) -> str:
        """Create a new branch for a run.

        Args:
            run_id: Identifier for the run

        Returns:
            Name of the created branch
        """
        logger.debug(f"Creating branch {branch_name}")

        # Check if the base branch exists
        base_exists = self.base_branch in self.list_branches()

        if base_exists:
            # Base branch exists, switch to it
            self.checkout(self.base_branch)
        else:
            # Base branch doesn't exist yet
            current_branch = self.get_current_branch()

            if current_branch:
                # Rename current branch to base branch
                self._run_git_command(["branch", "-m", current_branch, self.base_branch])
            else:
                # Create the base branch with an initial commit
                with open(self.outcome_dir / "README.md", "w") as f:
                    f.write("# Agent Execution Outputs\n\nThis repository contains outcomes from agent executions.\n")

                self.add("README.md")
                self.commit("Initial commit")
                self._run_git_command(["branch", "-m", self.base_branch])

        # Create and switch to the new branch
        self.checkout(branch_name, create=True)

        return branch_name

    def commit_run_outcomes(self, run_id: str, message: str, files: list[Path] | None = None) -> bool:
        """Commit all changes for a specific run.

        Args:
            run_id: Identifier for the run
            message: Commit message

        Returns:
            True if changes were committed, False otherwise
        """
        if files is None:
            files = []
        if not self.outcome_dir.exists():
            raise ValueError(f"Run directory {run_id} does not exist")

        # Add all files in the run directory
        for file in files:
            self.add(file)

        # Commit with message
        return self.commit(f"[{run_id}] {message}")

    def complete_run(
        self,
        run_id: str,
        status: str = "completed",
        commit_outcome: bool = True,
        commit_message: str | None = None,
        create_tag: bool = False,
        tag_name: str | None = None,
        tag_message: str | None = None,
    ) -> None:
        """Complete a run with a final commit and tag."""
        timestamp = datetime.now().isoformat(timespec="seconds")

        if commit_outcome:
            # Final commit
            self.commit_run_outcomes(
                run_id=run_id,
                message=f"Run {status} at {timestamp}",
            )

        if create_tag:
            # Create a tag for this run
            tag_name = tag_name or f"run-{run_id}-{status}"
            tag_message = tag_message or f"Run {run_id} {status} at {timestamp}"
            self.create_tag(tag_name, tag_message)

        # Return to base branch
        self.checkout(self.base_branch)

    def get_run_history(self, run_id: str | None = None) -> list[dict[str, str]]:
        """Get commit history for a run or all runs.

        Args:
            run_id: Optional run ID to filter history

        Returns:
            List of commit history entries
        """
        if run_id:
            # Check if there's a branch for this run
            branch_name = f"run/{run_id}"
            branches = self.list_branches()

            if branch_name in branches:
                # Branch exists, get its history
                return self.get_logs(branch=branch_name)
            else:
                # Fall back to path-based filtering
                return self.get_logs(path=run_id)

        # No specific run_id, get all logs
        return self.get_logs()

    def compare_runs(self, run_id1: str, run_id2: str, node_id: str | None = None) -> list[dict[str, str]]:
        """Compare outcomes between two runs, optionally for a specific node.

        Args:
            run_id1: First run ID
            run_id2: Second run ID
            node_id: Optional node ID to compare

        Returns:
            List of changes between runs
        """
        branch1 = f"run/{run_id1}"
        branch2 = f"run/{run_id2}"

        # Check if branches exist
        branches = self.list_branches()
        branches_exist = branch1 in branches and branch2 in branches

        if branches_exist:
            # Compare branches
            if node_id:
                return self.diff(
                    f"{branch1}:{run_id1}/{node_id}",
                    f"{branch2}:{run_id2}/{node_id}",
                )
            else:
                return self.diff(branch1, branch2)
        else:
            # Fall back to path-based comparison
            if node_id:
                path1 = f"{run_id1}/{node_id}"
                path2 = f"{run_id2}/{node_id}"
            else:
                path1 = run_id1
                path2 = run_id2
            return self.diff(path1, path2)

    def list_runs(self) -> list[str]:
        """List all run branches.

        Returns:
            List of run IDs
        """
        branches = self.list_branches("run/*")

        runs = []
        for branch_name in branches:
            # Extract run ID from branch name (run/run_id)
            run_id = branch_name.split("/", 1)[1] if "/" in branch_name else branch_name
            runs.append(run_id)

        return runs
