import json
import logging
import shutil
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from dhenara.agent.dsl.base import NodeInput
from dhenara.agent.dsl.events import EventBus, EventType
from dhenara.agent.observability.types import ObservabilitySettings
from dhenara.agent.shared.utils import get_project_identifier
from dhenara.agent.types.data import RunEnvParams
from dhenara.agent.utils.git import RunOutcomeRepository
from dhenara.agent.utils.io.artifact_manager import ArtifactManager

logger = logging.getLogger(__name__)


class RunContext:
    """Manages a single execution run of an agent."""

    def __init__(
        self,
        project_root: Path,
        agent_identifier: str,
        run_root: Path | None = None,
        run_id: str | None = None,
        observability_settings: ObservabilitySettings | None = None,
    ):
        if not observability_settings:
            observability_settings = ObservabilitySettings()

        self.project_root = project_root
        self.project_identifier = get_project_identifier(project_dir=self.project_root)
        self.agent_identifier = agent_identifier
        self.observability_settings = observability_settings

        self.run_root = run_root or project_root / "runs"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _run_id = run_id or f"run_{timestamp}_{uuid.uuid4().hex[:6]}"
        self.run_id = f"{self.agent_identifier}_{_run_id}"
        self.run_dir = self.run_root / self.run_id

        self.static_inputs_dir = self.run_dir / "static_inputs"
        self.static_inputs_dir.mkdir(parents=True, exist_ok=True)

        # Outcome is not inside the run id, there is a global outcome with
        # self.outcome_root = self.run_root
        self.outcome_dir = self.run_root / "outcome"

        # Outcome is the final outcome git repo, not just node outputs
        _outcome_repo_name = self.project_identifier
        self.outcome_repo_dir = self.outcome_dir / _outcome_repo_name

        self.start_time = datetime.now()
        self.end_time = None
        self.metadata = {}

        # Create directories
        self.run_dir.mkdir(parents=True, exist_ok=True)
        # self.state_dir = self.run_dir / ".state"
        # self.state_dir.mkdir(parents=True, exist_ok=True)
        self.trace_dir = self.run_dir / ".trace"
        self.trace_dir.mkdir(parents=True, exist_ok=True)

        self.outcome_dir.mkdir(parents=True, exist_ok=True)
        self.outcome_repo_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git outcome repository

        self.outcome_repo = RunOutcomeRepository(self.outcome_repo_dir)

        self.git_branch_name = f"run/{self.run_id}"
        self.outcome_repo.create_run_branch(self.git_branch_name)

        self.setup_observability()

        self.run_env_params = RunEnvParams(
            run_id=self.run_id,
            run_dir=str(self.run_dir),
            run_root=str(self.run_root),
            trace_dir=str(self.trace_dir),
        )
        self.artifact_manager = ArtifactManager(
            run_env_params=self.run_env_params,
            outcome_repo=self.outcome_repo,
        )

        self.event_bus = EventBus()
        self.static_inputs = {}  # For predefined inputs

        # Save initial metadata
        self._save_metadata()

    def register_node_static_input(self, node_id: str, input_data: NodeInput):
        """Register static input for a node."""

        self.static_inputs[node_id] = input_data

    def register_node_input_handler(self, handler: Callable):
        """Register a handler for input collection events."""
        self.event_bus.register(EventType.node_input_required, handler)

    def _save_metadata(self):
        """Save metadata about this run."""
        metadata = {
            "run_id": self.run_id,
            "created_at": self.start_time.isoformat(),
            "status": "initialized",
            **self.metadata,
        }
        with open(self.trace_dir / "dad_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

    def copy_input_files(
        self,
        source: Path | None = None,
        files: list | None = None,
    ):
        """Prepare input data and files for the run."""
        input_source_path = source or self.project_root / "agents" / self.agent_identifier / "inputs" / "data"

        if not input_source_path.exists():
            logger.warning(f"input_source_path {input_source_path} does not exists. No static input files copied")
            return

        # Save input data
        input_files = files or []

        if input_source_path:
            input_dir_path = input_source_path
            if input_dir_path.exists() and input_dir_path.is_dir():
                input_files += list(input_dir_path.glob("*"))

        # Copy input files if provided
        if input_files:
            for file_path in input_files:
                src = Path(file_path)
                if src.exists():
                    dst = self.static_inputs_dir / src.name
                    shutil.copy2(src, dst)

    def read_static_inputs(self):
        # Read initial inputs form the root input dir
        _input_file = self.static_inputs_dir / "static_inputs.json"

        if _input_file.exists():
            with open(self.static_inputs_dir / "static_inputs.json") as f:
                try:
                    _data = json.load(f)

                    for node_id, static_input in _data.items():
                        self.register_node_static_input(node_id, static_input)

                    logger.info(f"Successfully loaded Staic inputs from {_input_file}")
                except Exception as e:
                    logger.exception(f"read_static_inputs: Error: {e}")
        else:
            logger.info(f"Staic inputs are not initalized as no file exists in {_input_file}")

    def complete_run(self, status="completed"):
        """Mark the run as complete and save final metadata."""
        self.end_time = datetime.now()
        self.metadata["status"] = status
        self.metadata["completed_at"] = self.end_time.isoformat()
        self.metadata["duration_seconds"] = (self.end_time - self.start_time).total_seconds()
        self._save_metadata()

        # Complete run in git repository
        self.outcome_repo.complete_run(
            run_id=self.run_id,
            status=status,
            commit_outcome=True,
        )

    def setup_observability(self):
        """Set up observability for the run context."""
        # Setup observability
        from dhenara.agent.observability import configure_observability

        self.trace_file = self.trace_dir / "trace.jsonl"
        self.metrics_file = self.trace_dir / "metrics.jsonl"
        self.log_file = self.trace_dir / "logs.jsonl"

        # Create the trace directory if it doesn't exist
        self.trace_dir.mkdir(parents=True, exist_ok=True)

        # NOTE: Create the file, not inside observability package,
        # else will flag permission issues with isolated context
        Path(self.trace_file).touch()
        for file in [self.trace_file, self.log_file, self.metrics_file]:
            Path(file).touch()
            ## Ensure the file is readable and writable
            ##os.chmod(self.trace_file, 0o644)

        # Use agent_identifier as service name if not provided
        if not self.observability_settings.service_name:
            self.observability_settings.service_name = f"dhenara-dad-{self.agent_identifier}"

        # Set trace file path in settings
        self.observability_settings.trace_file_path = str(self.trace_file)
        self.observability_settings.metrics_file_path = str(self.metrics_file)
        self.observability_settings.log_file_path = str(self.log_file)

        # Use the centralized setup
        configure_observability(self.observability_settings)

        # TODO
        # self.initialize_observability_even_listing()

        # Log tracing info
        logger.info(f"Tracing enabled. Traces will be written to: {self.trace_file}")

    # TODO: Check if below is required
    def initialize_observability_even_listing(self) -> None:
        # Instrument the event bus to capture event-related spans
        original_publish = self.event_bus.publish

        async def instrumented_publish(event):
            # Get tracer
            from dhenara.agent.observability.tracing import get_tracer

            tracer = get_tracer("dhenara.agent.events")

            # Create span
            with tracer.start_as_current_span(
                f"event.{event.type}",
                attributes={
                    "event.type": event.type,
                    "event.nature": event.nature,
                },
            ) as span:
                try:
                    # Execute original publish
                    result = await original_publish(event)

                    # Add result info to span
                    if hasattr(event, "handled"):
                        span.set_attribute("event.handled", event.handled)

                    return result
                except Exception as e:
                    # Record error in span
                    span.record_exception(e)
                    span.set_attribute("error", str(e))
                    raise

        # Replace the event bus publish method
        self.event_bus.publish = instrumented_publish
