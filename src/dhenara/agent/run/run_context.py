import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from dhenara.agent.types.flow import FlowNodeInputs

from .output_repository import RunOutputRepository

logger = logging.getLogger(__name__)


class RunContext:
    """Manages a single execution run of an agent."""

    def __init__(
        self,
        project_root: Path,
        agent_name: str,
        run_root: Path | None = None,
        run_dir: str | None = None,
        input_dir: Path | None = None,
        input_file_name: str | None = None,
        output_dir: Path | None = None,
        output_file_name: str | None = None,
        state_dir: Path | None = None,
        run_id: str | None = None,
        initial_inputs: FlowNodeInputs | None = None,
    ):
        run_dir = run_dir or "runs"
        input_file_name = input_file_name or "input.json"
        output_file_name = output_file_name or "output.json"

        self.project_root = project_root
        self.run_root = run_root or project_root
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _run_id = run_id or f"run_{timestamp}_{uuid.uuid4().hex[:6]}"
        self.run_id = f"{agent_name}_{_run_id}"
        self.run_dir = self.run_root / run_dir
        self.input_dir_root = input_dir or self.run_dir / "input"
        self.input_dir = self.input_dir_root / self.run_id
        self.input_file_name = input_file_name
        self.output_dir_root = output_dir or self.run_dir / "output"
        self.output_dir = self.output_dir_root / self.run_id
        self.output_file_name = output_file_name
        self.state_dir = state_dir or self.run_dir / ".state" / self.run_id
        self.initial_inputs = initial_inputs

        self.start_time = datetime.now()
        self.end_time = None
        self.metadata = {}

        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git output repository
        self.output_repo = RunOutputRepository(self.run_dir / "output")
        self.output_repo.create_run_branch(self.run_id)

        # Save initial metadata
        self._save_metadata()

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

    def read_initial_inputs(self):
        # Read initial inputs form the root input dir
        with open(self.input_dir_root / "initial_inputs.json") as f:
            _data = json.load(f)
            try:
                return FlowNodeInputs(_data)
            except Exception as e:
                logger.exception(f"read_initial_inputs: Error: {e}")
                return None

    def prepare_input(self, input_data: dict, input_files: list | None = None):
        """Prepare input data and files for the run."""

        _initial_inputs = input_data.get("initial_inputs", None)
        if _initial_inputs:
            # Override
            self.initial_inputs = _initial_inputs

        if self.initial_inputs is None:
            self.initial_inputs = self.read_initial_inputs()

        if not isinstance(self.initial_inputs, FlowNodeInputs):
            logger.error(f"Imported input is not a FlowNodeInput: {type(self.initial_inputs)}")
            return

        # Save input data
        if input_files is None:
            input_files = []

        with open(self.input_dir / self.input_file_name, "w") as f:
            json.dump(input_data, f, indent=2)

        if self.input_dir:
            input_dir_path = Path(self.input_dir)
            if input_dir_path.exists() and input_dir_path.is_dir():
                input_files += list(input_dir_path.glob("*"))

        # TODO: Something is ambigious here. what sort of inputs & how to hanlde them per node

        # TODO
        ## Copy input files if provided
        # if input_files:
        #    for file_path in input_files:
        #        src = Path(file_path)
        #        if src.exists():
        #            dst = self.input_dir / src.name
        #            shutil.copy2(src, dst)

    def save_output(self, node_id, output_data, commit=True):
        """Save output from a node execution."""
        # Create node output directory
        node_dir = self.output_dir / node_id
        node_dir.mkdir(exist_ok=True)

        # Save output data
        output_file_name = node_dir / self.output_file_name
        with open(output_file_name, "w") as f:
            json.dump(output_data, f, indent=2)

        # Commit changes if requested
        if commit:
            self.output_repo.commit_run_outputs(self.run_id, f"Add output from node {node_id}")

        return output_file_name

    def complete_run(self, status="completed"):
        """Mark the run as complete and save final metadata."""
        self.end_time = datetime.now()
        self.metadata["status"] = status
        self.metadata["completed_at"] = self.end_time.isoformat()
        self.metadata["duration_seconds"] = (self.end_time - self.start_time).total_seconds()
        self._save_metadata()

        # Complete run in git repository
        self.output_repo.complete_run(self.run_id, status)
