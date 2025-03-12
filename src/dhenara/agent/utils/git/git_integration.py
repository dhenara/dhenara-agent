# dhenara/agent/utils/git_integration.py
import os
import subprocess
from pathlib import Path

from github import Github


class GitIntegration:
    """Git integration utilities for agent operations."""

    def __init__(self, repo_path: str, github_token: str | None = None):
        self.repo_path = repo_path
        self.github_token = github_token
        self.github_client = Github(github_token) if github_token else None

    def initialize_repo(self) -> bool:
        """Initialize a new git repository."""
        try:
            os.chdir(self.repo_path)
            subprocess.run(["git", "init"], check=True, stdout=subprocess.PIPE)

            # Create .gitignore
            gitignore_path = Path(self.repo_path) / ".gitignore"
            if not gitignore_path.exists():
                with open(gitignore_path, "w") as f:
                    f.write("__pycache__/\n*.py[cod]\n*$py.class\n.env\n.venv\nenv/\nvenv/\n*.log\n.DS_Store\nnode_modules/\n")

            return True
        except Exception as e:
            print(f"Error initializing git repo: {e}")
            return False

    def stage_and_commit(self, message: str, file_paths: list[str] | None = None) -> bool:
        """Stage and commit changes."""
        try:
            os.chdir(self.repo_path)
            if file_paths:
                for file_path in file_paths:
                    subprocess.run(["git", "add", file_path], check=True)
            else:
                subprocess.run(["git", "add", "."], check=True)

            subprocess.run(["git", "commit", "-m", message], check=True)
            return True
        except Exception as e:
            print(f"Error committing changes: {e}")
            return False

    def create_branch_for_task(self, task_name: str) -> str:
        """Create a branch for a specific task."""
        # Create a safe branch name
        branch_name = f"feature/{task_name.lower().replace(' ', '-')}"

        try:
            os.chdir(self.repo_path)
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            return branch_name
        except Exception as e:
            print(f"Error creating branch: {e}")
            return ""
