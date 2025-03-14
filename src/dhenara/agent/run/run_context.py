import json
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path


class RunContext:
    """Manages a single execution run of an agent."""

    def __init__(
        self,
        project_root: Path,
        run_root: Path,
        run_dir: str = "runs",
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        state_dir: Path | None = None,
        run_id: str | None = None,
    ):
        self.project_root = project_root
        self.run_root = run_root or project_root
        self.run_id = run_id or f"run_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        self.run_dir = self.run_root / run_dir
        self.input_dir = input_dir or self.run_dir / "input" / self.run_id
        self.output_dir = output_dir or self.run_dir / "output" / self.run_id
        self.state_dir = state_dir or self.run_dir / ".state" / self.run_id
        self.start_time = datetime.now()
        self.end_time = None
        self.metadata = {}

        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git repo for this run's output if it doesn't exist
        self._init_output_repo()

        # Save initial metadata
        self._save_metadata()

    def _init_output_repo(self):
        """Initialize or update git repo for outputs."""
        # Check if git exists in parent output directory
        git_dir = self.run_dir / "output" / ".git"
        if not git_dir.exists():
            subprocess.run(
                ["git", "init"],
                cwd=self.run_dir / "output",
                check=True,
                stdout=subprocess.PIPE,
            )

    def _save_metadata(self):
        """Save metadata about this run."""
        metadata = {
            "run_id": self.run_id,
            "created_at": self.start_time.isoformat(),
            "status": "initialized",
            **self.metadata,
        }

        with open(self.state_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

    def prepare_input(self, input_data, input_files=None):
        """Prepare input data and files for the run."""
        # Save input data
        with open(self.input_dir / "input.json", "w") as f:
            json.dump(input_data, f, indent=2)

        # Copy input files if provided
        if input_files:
            for file_path in input_files:
                src = Path(file_path)
                if src.exists():
                    dst = self.input_dir / src.name
                    shutil.copy2(src, dst)

    def save_output(self, node_id, output_data, commit=True):
        """Save output from a node execution."""
        # Create node output directory
        node_dir = self.output_dir / node_id
        node_dir.mkdir(exist_ok=True)

        # Save output data
        output_file = node_dir / "output.json"
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        # Commit changes if requested
        if commit:
            self.commit_outputs(f"Add output from node {node_id}")

        return output_file

    def commit_outputs(self, message):
        """Commit changes to the output repository."""
        # First add all files
        subprocess.run(["git", "add", "."], cwd=self.run_dir / "output", check=True)

        # Then commit with message
        try:
            subprocess.run(
                ["git", "commit", "-m", f"[{self.run_id}] {message}"],
                cwd=self.run_dir / "output",
                check=True,
            )
        except subprocess.CalledProcessError:
            # No changes to commit, that's fine
            pass

    def complete_run(self, status="completed"):
        """Mark the run as complete and save final metadata."""
        self.end_time = datetime.now()
        self.metadata["status"] = status
        self.metadata["completed_at"] = self.end_time.isoformat()
        self.metadata["duration_seconds"] = (
            self.end_time - self.start_time
        ).total_seconds()

        self._save_metadata()
        self.commit_outputs(f"Complete run with status: {status}")

        # Create a tag for this run
        subprocess.run(
            ["git", "tag", f"run-{self.run_id}"],
            cwd=self.run_dir / "output",
            check=True,
        )
