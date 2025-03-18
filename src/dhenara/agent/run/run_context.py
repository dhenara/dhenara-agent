import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from dhenara.agent.shared.utils import get_project_identifier
from dhenara.agent.types.data import RunEnvParams
from dhenara.agent.types.flow import FlowNodeInputs
from dhenara.agent.utils.git import RunOutcomeRepository
from dhenara.agent.utils.io.artifact_manager import ArtifactManager

logger = logging.getLogger(__name__)


class RunContext:
    """Manages a single execution run of an agent."""

    def __init__(
        self,
        project_root: Path,
        agent_identifier: str,
        input_source_path: Path | None = None,
        initial_inputs: FlowNodeInputs | None = None,
        run_root: Path | None = None,
        run_id: str | None = None,
        # run_dir: str | None = None,
        # output_dir: str | None = None,
        # state_dir: str | None = None,
    ):
        self.project_root = project_root
        self.project_identifier = get_project_identifier(project_dir=self.project_root)
        self.agent_identifier = agent_identifier

        self.run_root = run_root or project_root / "runs"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _run_id = run_id or f"run_{timestamp}_{uuid.uuid4().hex[:6]}"
        self.run_id = f"{self.agent_identifier}_{_run_id}"
        self.run_dir = self.run_root / self.run_id

        _input_dir = "input"
        _output_dir = "output"
        _state_dir = ".state"

        self.input_source_path = input_source_path or self.project_root / "agents" / agent_identifier / "inputs"
        self.initial_inputs = initial_inputs

        self.input_dir = self.run_dir / _input_dir
        self.output_dir = self.run_dir / _output_dir
        self.state_dir = self.run_dir / _state_dir

        # Outcome is not inside the run id, there is a global outcome with
        # self.outcome_root = self.run_root
        self.outcome_dir = self.run_root / "outcome"

        # Outcome is the final outcome git repo, not just node outputs
        _outcome_repo_name = self.project_identifier
        self.outcome_repo_dir = self.outcome_dir / _outcome_repo_name

        self.start_time = datetime.now()
        self.end_time = None
        self.metadata = {}

        if not self.input_source_path.exists():
            raise ValueError(f"input_source_path {self.input_source_path} does not exists")

        # Create directories
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.outcome_dir.mkdir(parents=True, exist_ok=True)
        self.outcome_repo_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git outcome repository

        self.outcome_repo = RunOutcomeRepository(self.outcome_repo_dir)
        self.outcome_repo.create_run_branch(self.run_id)

        # Save initial metadata
        self._save_metadata()

        self.run_env_params = RunEnvParams(
            run_id=self.run_id,
            project_root=str(self.project_root),
            project_identifier=str(self.project_identifier),
            agent_identifier=str(self.agent_identifier),
            run_dir=str(self.run_dir),
            input_dir=str(self.input_dir),
            output_dir=str(self.output_dir),
            state_dir=str(self.state_dir),
            outcome_dir=str(self.outcome_dir),
            outcome_repo_dir=str(self.outcome_repo_dir),
        )
        self.artifact_manager = ArtifactManager(
            run_env_params=self.run_env_params,
            outcome_repo=self.outcome_repo,
        )

        # FlowContext
        self.flow_context = None

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
        with open(self.input_dir / "initial_inputs.json") as f:
            _data = json.load(f)
            try:
                return FlowNodeInputs(_data)
            except Exception as e:
                logger.exception(f"read_initial_inputs: Error: {e}")
                return None

    def prepare_input(self, input_files: list | None = None):
        """Prepare input data and files for the run."""
        # Save input data
        if input_files is None:
            input_files = []

        if self.input_source_path:
            input_dir_path = self.input_source_path
            if input_dir_path.exists() and input_dir_path.is_dir():
                input_files += list(input_dir_path.glob("*"))

        # Copy input files if provided
        if input_files:
            for file_path in input_files:
                src = Path(file_path)
                if src.exists():
                    dst = self.input_dir / src.name
                    shutil.copy2(src, dst)

    def init_inputs(self, input_data: dict):
        _initial_inputs = input_data.get("initial_inputs", None)
        if _initial_inputs:
            # Override
            self.initial_inputs = _initial_inputs

        # Read the initial inputs
        if self.initial_inputs is None:
            self.initial_inputs = self.read_initial_inputs()

        if not isinstance(self.initial_inputs, FlowNodeInputs):
            logger.error(f"Imported input is not a FlowNodeInput: {type(self.initial_inputs)}")

    def complete_run(self, status="completed"):
        """Mark the run as complete and save final metadata."""
        self.end_time = datetime.now()
        self.metadata["status"] = status
        self.metadata["completed_at"] = self.end_time.isoformat()
        self.metadata["duration_seconds"] = (self.end_time - self.start_time).total_seconds()
        self._save_metadata()

        # Complete run in git repository
        self.outcome_repo.complete_run(self.run_id, status)
