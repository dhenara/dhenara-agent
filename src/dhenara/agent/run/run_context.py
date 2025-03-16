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
        input_root: Path | None = None,
        initial_inputs: FlowNodeInputs | None = None,
        run_root: Path | None = None,
        run_dir: str | None = None,
        output_dir: str | None = None,
        # state_dir: str | None = None,
        run_id: str | None = None,
    ):
        self.project_root = project_root
        self.agent_name = agent_name

        self.run_root = run_root or project_root
        _run_dir = run_dir or "runs"
        self.run_dir = self.run_root / _run_dir

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _run_id = run_id or f"run_{timestamp}_{uuid.uuid4().hex[:6]}"
        _output_dir = output_dir or "output"

        self.input_root = input_root or self.run_dir / "input"
        self.initial_inputs = initial_inputs

        self.run_id = f"{self.agent_name}_{_run_id}"

        self.output_root = self.run_dir / _output_dir
        self.output_dir = self.output_root / self.run_id
        self.state_dir = self.output_dir / ".state" / self.run_id

        # Outcome is the final outcome git repo, not just node outputs
        self.outcome_root = self.output_root / "outcome"
        _outcome_repo_name = self.agent_name  # TODO_FUTURE:  Pass as cmd line arg
        self.outcome_repo = self.outcome_root / _outcome_repo_name

        self.start_time = datetime.now()
        self.end_time = None
        self.metadata = {}

        if not self.input_root.exists():
            raise ValueError(f"input_root {self.input_root} does not exists")

        # Create directories
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.outcome_root.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.outcome_repo.mkdir(parents=True, exist_ok=True)

        # Initialize git outcome repository

        self.output_repo = RunOutputRepository(self.outcome_repo)
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
        with open(self.input_root / "initial_inputs.json") as f:
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

        if self.input_root:
            input_dir_path = Path(self.input_root)
            if input_dir_path.exists() and input_dir_path.is_dir():
                input_files += list(input_dir_path.glob("*"))

        # TODO: Something is ambigious here. what sort of inputs & how to hanlde them per node

        # TODO
        ## Copy input files if provided
        # if input_files:
        #    for file_path in input_files:
        #        src = Path(file_path)
        #        if src.exists():
        #            dst = self.input_root / src.name
        #            shutil.copy2(src, dst)

    def save_output(self, node_id, commit=True):
        """Save output from a node execution."""
        # Create node output directory
        node_dir = self.output_dir / node_id
        node_dir.mkdir(exist_ok=True)

        # TODO
        # Extract output data from flow context/ ?

        # # Save output data
        # output_file = node_dir / output_file_name
        # with open(output_file, "w") as f:
        #     json.dump(output_data, f, indent=2)

        # # Commit changes if requested
        # if commit:
        #     self.output_repo.commit_run_outputs(self.run_id, f"Add output from node {node_id}")

        # return output_file

    def complete_run(self, status="completed"):
        """Mark the run as complete and save final metadata."""
        self.end_time = datetime.now()
        self.metadata["status"] = status
        self.metadata["completed_at"] = self.end_time.isoformat()
        self.metadata["duration_seconds"] = (self.end_time - self.start_time).total_seconds()
        self._save_metadata()

        # Complete run in git repository
        self.output_repo.complete_run(self.run_id, status)
