# dhenara/agent/utils/git/base.py
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitBase:
    """Base class for Git operations throughout the package.

    This class provides common Git operations that can be reused
    by various components that need to interact with Git repositories.
    """

    def __init__(
        self,
        repo_path: str | Path,
    ):
        """Initialize with repository path.

        Args:
            repo_path: Path to the Git repository.
        """
        self.repo_path = Path(repo_path)
        self._git_available = self._check_git_available()

    def clone_repository(self, url: str, branch: str | None = None, depth: int | None = None) -> bool:
        """
        Clone a repository from the given URL

        Args:
            url: Repository URL to clone
            branch: Optional branch to clone
            depth: Optional depth parameter for shallow clones

        Returns:
            True if cloning was successful, False otherwise
        """
        try:
            cmd = ["clone", url, str(self.repo_path)]

            if branch:
                cmd.extend(["--branch", branch])

            if depth:
                cmd.extend(["--depth", str(depth)])

            _result = subprocess.run(["git", *cmd], check=True, capture_output=True, text=True)

            logger.info(f"Successfully cloned repository from {url}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e.stderr}")
            return False

    def _check_git_available(self) -> bool:
        """Check if git is available on the system."""
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Git is not available on this system")
            return False

    def _run_git_command(
        self, command: list[str], check: bool = True, capture_output: bool = True
    ) -> tuple[int, str, str]:
        """Run a git command and handle errors consistently.

        Args:
            command: Git command and arguments
            check: Whether to raise exception on non-zero exit
            capture_output: Whether to capture and return output

        Returns:
            Tuple of (return code, stdout, stderr)
        """
        if not self._git_available:
            logger.error("Cannot run git command, git not available")
            return 1, "", "Git not available"

        try:
            cmd = ["git", *command]
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                check=check,
                text=True,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
            )
            return result.returncode, result.stdout or "", result.stderr or ""
        except subprocess.CalledProcessError as e:
            if check:
                logger.error(f"Git command failed: {e}")
                raise
            return e.returncode, e.stdout or "", e.stderr or ""

    def _git_init(self) -> bool:
        """Initialize a new git repository.

        Returns:
            bool: True if successful
        """
        if (self.repo_path / ".git").exists():
            logger.info(f"Repository already initialized in {self.repo_path}")
            return True

        try:
            returncode, stdout, stderr = self._run_git_command(["init"])
            return returncode == 0
        except Exception as e:
            logger.exception(f"Failed to initialize repository: {e}")
            return False

    def init_repo(
        self,
        readme_content: str | None = None,
        commit: bool = True,
    ) -> None:
        """Initialzie/Ensure the outcome directory is a git repository with a main branch."""
        if not self.repo_exists():
            logger.info(f"Initializing git repository in {self.repo_path}")
            status = self._git_init()

            if not status:
                logger.error(f"Failed to initializing git repository in {self.repo_path}")
                return False

        # Configure git
        self._run_git_command(["config", "core.bigFileThreshold", "10m"])

        # Create initial commit in main branch
        if readme_content:
            readme_file = self.repo_path / "README.md"
            with open(readme_file, "w") as f:
                f.write(readme_content)

            self.add(readme_file)
            self.commit("Initial commit")

    def ensure_repo(self) -> None:
        """Ensure the directory is a git repository with a base branch."""
        if not self.repo_exists():
            self.init_repo()

            # Ensure we're on main branch (newer git uses 'main', older uses 'master')
            current_branch = self.get_current_branch()

            # If not on main, rename the branch
            if current_branch and current_branch != self.base_branch:
                self._run_git_command(["branch", "-m", current_branch, self.base_branch])

    def repo_exists(self) -> bool:
        """Check if a git repository exists.

        Returns:
            bool: True if repository exists
        """
        return (self.repo_path / ".git").exists()

    def add(self, paths: Path | list[Path]) -> bool:
        """Add files to git staging.

        Args:
            paths: Single path or list of paths to add

        Returns:
            bool: True if successful
        """
        if isinstance(paths, Path):
            paths = [paths]

        try:
            for path in paths:
                returncode, stdout, stderr = self._run_git_command(["add", path])
                if returncode != 0:
                    return False
            return True
        except Exception as e:
            logger.exception(f"Failed to add files: {e}")
            return False

    def commit(self, message: str) -> bool:
        """Commit staged changes.

        Args:
            message: Commit message

        Returns:
            bool: True if successful
        """
        try:
            returncode, stdout, stderr = self._run_git_command(["commit", "-m", message], check=False)
            # Return True if commit succeeded (0) or if there was nothing to commit (1 with specific message)
            return returncode == 0 or (returncode == 1 and "nothing to commit" in stderr)
        except Exception as e:
            logger.exception(f"Failed to commit: {e}")
            return False

    def get_current_branch(self) -> str | None:
        """Get name of current branch.

        Returns:
            str: Current branch name or None if failed
        """
        try:
            returncode, stdout, stderr = self._run_git_command(["branch", "--show-current"])
            return stdout.strip() if returncode == 0 else None
        except Exception as e:
            logger.exception(f"Failed to get current branch: {e}")
            return None

    def checkout(self, branch: str, create: bool = False) -> bool:
        """Checkout a branch.

        Args:
            branch: Branch name to checkout
            create: Whether to create branch if it doesn't exist

        Returns:
            bool: True if successful
        """
        try:
            cmd = ["checkout"]
            if create:
                cmd.append("-b")
            cmd.append(branch)

            returncode, stdout, stderr = self._run_git_command(cmd, check=False)
            return returncode == 0
        except Exception as e:
            logger.exception(f"Failed to checkout branch {branch}: {e}")
            return False

    def create_tag(self, tag_name: str, message: str | None = None) -> bool:
        """Create a git tag.

        Args:
            tag_name: Name of the tag
            message: Optional tag message

        Returns:
            bool: True if successful
        """
        try:
            cmd = ["tag"]
            if message:
                cmd.extend(["-a", tag_name, "-m", message])
            else:
                cmd.append(tag_name)

            returncode, stdout, stderr = self._run_git_command(cmd)
            return returncode == 0
        except Exception as e:
            logger.exception(f"Failed to create tag {tag_name}: {e}")
            return False

    def get_logs(
        self,
        branch: str | None = None,
        path: str | None = None,
        format_str: str = "%h|%ad|%s",
        date_format: str = "iso",
    ) -> list[dict[str, str]]:
        """Get commit history.

        Args:
            branch: Branch to get logs from
            path: Filter logs to specific path
            format_str: Format string for log output
            date_format: Date format for logs

        Returns:
            List of commit dictionaries
        """
        try:
            cmd = ["log", f"--pretty=format:{format_str}", f"--date={date_format}"]

            if branch:
                cmd.append(branch)

            if path:
                cmd.extend(["--", path])

            returncode, stdout, stderr = self._run_git_command(cmd, check=False)

            if returncode != 0 or not stdout.strip():
                return []

            history = []
            for line in stdout.strip().split("\n"):
                if line:
                    parts = line.split("|", 2)
                    if len(parts) >= 3:
                        commit_hash, date, message = parts
                        history.append({"commit": commit_hash, "date": date, "message": message})

            return history
        except Exception as e:
            logger.exception(f"Failed to get logs: {e}")
            return []

    def diff(self, source: str, target: str, name_status: bool = True) -> list[dict[str, str]]:
        """Get differences between commits, branches, or paths.

        Args:
            source: Source reference (commit, branch, path)
            target: Target reference
            name_status: Whether to get name-status format

        Returns:
            List of changes
        """
        try:
            cmd = ["diff"]
            if name_status:
                cmd.append("--name-status")

            cmd.extend([source, target])

            returncode, stdout, stderr = self._run_git_command(cmd, check=False)

            if returncode != 0 or not stdout.strip():
                return []

            changes = []
            for line in stdout.strip().split("\n"):
                if line and "\t" in line:
                    status, file_path = line.split("\t", 1)
                    changes.append({"status": status, "path": file_path})

            return changes
        except Exception as e:
            logger.exception(f"Failed to get diff: {e}")
            return []

    def list_branches(self, pattern: str | None = None) -> list[str]:
        """List branches, optionally filtered with a pattern.

        Args:
            pattern: Optional filter pattern

        Returns:
            List of branch names
        """
        try:
            cmd = ["branch", "--list"]
            if pattern:
                cmd.append(pattern)

            returncode, stdout, stderr = self._run_git_command(cmd, check=False)

            if returncode != 0 or not stdout.strip():
                return []

            branches = []
            for line in stdout.strip().split("\n"):
                if line.strip():
                    # Remove leading decoration (* for current branch)
                    branch_name = line.strip().replace("* ", "")
                    branches.append(branch_name)

            return branches
        except Exception as e:
            logger.exception(f"Failed to list branches: {e}")
            return []
