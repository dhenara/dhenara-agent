import subprocess
from pathlib import Path


class OutputRepository:
    """Manages the git repository for agent outputs."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self._ensure_repo()

    def _ensure_repo(self):
        """Ensure the output directory is a git repository."""
        git_dir = self.output_dir / ".git"
        if not git_dir.exists():
            # Initialize new repo
            subprocess.run(["git", "init"], cwd=self.output_dir, check=True, stdout=subprocess.PIPE)

            # Configure git to handle large files
            subprocess.run(["git", "config", "core.bigFileThreshold", "10m"], cwd=self.output_dir, check=True)

            # Create initial commit
            with open(self.output_dir / "README.md", "w") as f:
                f.write("# Agent Execution Outputs\n\nThis repository contains outputs from agent executions.\n")

            subprocess.run(["git", "add", "README.md"], cwd=self.output_dir, check=True)

            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.output_dir, check=True)

    def commit_run_outputs(self, run_id, message):
        """Commit all changes for a specific run."""
        run_dir = self.output_dir / run_id
        if not run_dir.exists():
            raise ValueError(f"Run directory {run_id} does not exist")

        # Add all files in the run directory
        subprocess.run(["git", "add", run_id], cwd=self.output_dir, check=True)

        # Commit with message
        try:
            subprocess.run(["git", "commit", "-m", f"[{run_id}] {message}"], cwd=self.output_dir, check=True)
            return True
        except subprocess.CalledProcessError:
            # No changes to commit
            return False

    def tag_run(self, run_id, tag=None, message=None):
        """Create a git tag for a run."""
        tag = tag or f"run-{run_id}"

        if message:
            subprocess.run(["git", "tag", "-a", tag, "-m", message], cwd=self.output_dir, check=True)
        else:
            subprocess.run(["git", "tag", tag], cwd=self.output_dir, check=True)

    def get_run_history(self, run_id=None):
        """Get commit history for a run or all runs."""
        if run_id:
            cmd = ["git", "log", "--pretty=format:%h|%ad|%s", "--date=iso", "--", run_id]
        else:
            cmd = ["git", "log", "--pretty=format:%h|%ad|%s", "--date=iso"]

        result = subprocess.run(cmd, cwd=self.output_dir, check=True, stdout=subprocess.PIPE, text=True)

        history = []
        for line in result.stdout.strip().split("\n"):
            if line:
                commit_hash, date, message = line.split("|", 2)
                history.append({"commit": commit_hash, "date": date, "message": message})

        return history

    def compare_runs(self, run_id1, run_id2, node_id=None):
        """Compare outputs between two runs, optionally for a specific node."""
        if node_id:
            path1 = f"{run_id1}/{node_id}"
            path2 = f"{run_id2}/{node_id}"
        else:
            path1 = run_id1
            path2 = run_id2

        cmd = ["git", "diff", "--name-status", path1, path2]
        result = subprocess.run(cmd, cwd=self.output_dir, check=True, stdout=subprocess.PIPE, text=True)

        changes = []
        for line in result.stdout.strip().split("\n"):
            if line:
                status, file_path = line.split("\t", 1)
                changes.append({"status": status, "path": file_path})

        return changes
