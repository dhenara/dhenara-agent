# src/dhenara_agent/core/workspace.py
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

# TODO
import git


class Workspace:
    """Manages the execution environment for agents."""

    def __init__(self, base_dir=None, workspace_id=None):
        self.base_dir = Path(base_dir or tempfile.gettempdir()) / "dhenara-agent"
        self.workspace_id = workspace_id or str(uuid.uuid4())
        self.workspace_path = self.base_dir / self.workspace_id
        self.input_path = self.workspace_path / "input"
        self.output_path = self.workspace_path / "output"
        self.state_path = self.workspace_path / "state"

    def setup(self):
        """Initialize the workspace directory structure."""
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.input_path.mkdir(exist_ok=True)
        self.output_path.mkdir(exist_ok=True)
        self.state_path.mkdir(exist_ok=True)
        return self

    def clone_repository(self, repo_url, target_dir=None, branch="main"):
        """Clone a git repository into the input directory."""
        target = self.input_path / (target_dir or Path(repo_url).stem)
        git.Repo.clone_from(repo_url, target, branch=branch)
        return target

    def add_file(self, source_path, target_path=None):
        """Add a file to the input directory."""
        source = Path(source_path)
        target = self.input_path / (target_path or source.name)
        target.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        return target

    def get_output_dir(self, name=None):
        """Get an output directory, creating it if needed."""
        if name:
            output_dir = self.output_path / name
            output_dir.mkdir(exist_ok=True)
            return output_dir
        return self.output_path

    def save_artifact(self, content, filename, output_dir=None):
        """Save content as an artifact in the output directory."""
        output_path = self.get_output_dir(output_dir) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, (str, bytes)):
            mode = "w" if isinstance(content, str) else "wb"
            with open(output_path, mode) as f:
                f.write(content)
        else:
            # Assume it's a file-like object
            with open(output_path, "wb") as f:
                shutil.copyfileobj(content, f)

        return output_path

    def cleanup(self):
        """Clean up the workspace."""
        if self.workspace_path.exists():
            shutil.rmtree(self.workspace_path)


@contextmanager
def create_workspace(base_dir=None, workspace_id=None):
    """Context manager for creating and cleaning up workspaces."""
    workspace = Workspace(base_dir, workspace_id).setup()
    try:
        yield workspace
    finally:
        workspace.cleanup()
