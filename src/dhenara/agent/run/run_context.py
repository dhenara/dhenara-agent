import json
import logging
import os
import shutil
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from dhenara.agent.dsl.base import NodeInput
from dhenara.agent.dsl.base.context_registry import ExecutionContextRegistry
from dhenara.agent.dsl.events import EventBus, EventType
from dhenara.agent.observability.types import ObservabilitySettings
from dhenara.agent.run.registry import resource_config_registry
from dhenara.agent.types.data import RunEnvParams
from dhenara.agent.utils.git import RunOutcomeRepository
from dhenara.agent.utils.io.artifact_manager import ArtifactManager
from dhenara.agent.utils.shared import get_project_identifier
from dhenara.ai.types.resource import ResourceConfig

logger = logging.getLogger(__name__)


class RunContext:
    """Manages a single execution run of an agent."""

    def __init__(
        self,
        root_component_id: str,
        project_root: Path,
        run_root: Path | None = None,
        run_id: str | None = None,
        observability_settings: ObservabilitySettings | None = None,
        #  for re-run functionality
        previous_run_id: str | None = None,
        start_hierarchy_path: str | None = None,
        # Static inputs
        input_source: Path | None = None,
    ):
        self.root_component_id = root_component_id

        if not observability_settings:
            observability_settings = ObservabilitySettings()

        self.project_root = project_root
        self.project_identifier = get_project_identifier(project_dir=self.project_root)
        # self.agent_identifier = agent_identifier
        self.observability_settings = observability_settings
        self.input_source = input_source

        self.run_root = run_root or project_root / "runs"

        # Store re-run parameters
        self.run_id = run_id
        self.previous_run_id = previous_run_id
        self.start_hierarchy_path = start_hierarchy_path
        self.execution_context_registry = ExecutionContextRegistry(
            enable_caching=True,
        )

        self.event_bus = EventBus()
        self.setup_completed = False
        self.created_at = datetime.now()

    def set_previous_run(
        self,
        previous_run_id: str,
        start_hierarchy_path: str | None = None,
    ):
        self.previous_run_id = previous_run_id
        self.start_hierarchy_path = start_hierarchy_path

    def setup_run(self, run_id_prefix: str | None = None):
        # Indicates if this is a rerun of a previous execution
        self.is_rerun = self.previous_run_id is not None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_or_rerun = "rerun" if self.is_rerun else "run"
        _prefix = f"{run_id_prefix}_" if run_id_prefix else ""
        self.run_id = f"{_prefix}{run_or_rerun}_{timestamp}_{uuid.uuid4().hex[:6]}"
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

        # Initialize previous run context
        self.previous_run_dir = None
        if self.previous_run_id:
            self.previous_run_dir = self.run_root / self.previous_run_id
            if not self.previous_run_dir.exists():
                logger.error(f"Previous run directory does not exist: {self.previous_run_dir}")
                self.previous_run_id = None
                self.previous_run_dir = None

        # Setup observability with rerun info
        self.setup_observability()

        # Add rerun info to metadata
        if self.is_rerun:
            self.metadata["rerun_info"] = {
                "previous_run_id": self.previous_run_id,
                "start_hierarchy_path": self.start_hierarchy_path,
            }

        # Create run environment parameters
        self.run_env_params = RunEnvParams(
            run_id=self.run_id,
            run_dir=str(self.run_dir),
            run_root=str(self.run_root),
            trace_dir=str(self.trace_dir),
            outcome_repo_dir=str(self.outcome_repo_dir) if self.outcome_repo_dir else None,
        )

        # Initialize artifact manager
        self.artifact_manager = ArtifactManager(
            run_env_params=self.run_env_params,
            outcome_repo=self.outcome_repo,
        )
        # Intit resource config
        self.resource_config: ResourceConfig = self.get_resource_config()

        self.static_inputs = {}

        # Save initial metadata
        self._save_metadata()

        # mark setup completed
        self.setup_completed = True

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
            "created_at": self.created_at.isoformat(),
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
        input_source_path = source or self.input_source

        if not (input_source_path and input_source_path.exists()):
            logger.info(f"input_source_path {input_source_path} does not exists. No static input files copied")
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

    def complete_run(
        self,
        status="completed",
        error_msg: str | None = None,
    ):
        """Mark the run as complete and save final metadata."""
        if self.setup_completed:  # Failed after setup_run()
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
        else:
            # TODO_FUTURE: Record to a global recording system?
            logger.error(f"Completed run even before run_context setup. Error: {error_msg}")

    async def load_from_previous_run(
        self,
        is_component: bool,
        hierarchy_path: str,
        copy_artifacts: bool = True,
    ) -> dict | None:
        """Copy artifacts from previous run up to the start node."""
        if not self.previous_run_dir or not self.previous_run_dir.exists():
            logger.error(f"Cannot copy artifacts: Previous run directory not found. Looked for {self.previous_run_dir}")
            return

        if copy_artifacts:
            await self._copy_previous_run_artifacts(
                hierarchy_path=hierarchy_path,
                is_component=is_component,
            )
            logger.info(f"Copied previous execution result artifacts for {hierarchy_path}")

        return self.load_previous_run_execution_result_dict(
            hierarchy_path=hierarchy_path,
            is_component=is_component,
        )

    async def _copy_previous_run_artifacts(
        self,
        hierarchy_path: str,
        is_component: bool,
    ):
        """Copy artifacts for a specific node/component from previous run."""
        if not self.previous_run_dir:
            return

        # Determine the hierarchy path for this node
        try:
            element_hier_dir = hierarchy_path.replace(".", os.sep)
        except Exception as e:
            logger.error(f"Error while deriving heirarchy for prevoious run artifacts: Error: {e}")
            return

        # Define source and target directories
        src_input_dir = self.previous_run_dir / element_hier_dir
        dst_input_dir = self.run_dir / element_hier_dir

        # Ensure target directory exists
        dst_input_dir.mkdir(parents=True, exist_ok=True)

        # NOTE: Currently there us nothing to copy for components
        if is_component:
            return

        # try:
        #    # Use glob to copy files instead of trying to use wildcard with copy2
        #    import glob

        #    for file_path in glob.glob(str(src_input_dir / "*")):
        #        if os.path.isfile(file_path):
        #            shutil.copy2(file_path, dst_input_dir)
        #        elif os.path.isdir(file_path):
        #            dst_subdir = dst_input_dir / os.path.basename(file_path)
        #            shutil.copytree(file_path, dst_subdir, dirs_exist_ok=True)

        #    logger.debug(f"Copied dirs for {hierarchy_path}")
        # except Exception as e:
        #    logger.error(f"Failed to copy dirs for {hierarchy_path}: {e}")

        if src_input_dir.exists():
            # Copy input, output, and outcome files
            for file_name in ["outcome.json", "result.json"]:
                src_file = src_input_dir / file_name
                if src_file.exists():
                    dst_file = dst_input_dir / file_name
                    try:
                        shutil.copy2(src_file, dst_file)
                        logger.debug(f"Copied {file_name} for {hierarchy_path}")
                    except Exception as e:
                        logger.warning(f"Failed to copy {file_name} for {hierarchy_path}: {e}")

            ## Copy any other files in the directory
            # for src_file in src_input_dir.glob("*"):
            #    if src_file.is_file() and src_file.name not in ["input.json", "output.json", "outcome.json"]:
            #        dst_file = dst_input_dir / src_file.name
            #        try:
            #            shutil.copy2(src_file, dst_file)
            #            logger.debug(f"Copied additional file {src_file.name} for node {node_id}")
            #        except Exception as e:
            #            logger.warning(f"Failed to copy additional file {src_file.name} for node {node_id}: {e}")

    def load_previous_run_execution_result_dict(
        self,
        hierarchy_path: str,
        is_component: bool,
    ) -> dict | None:
        """Copy artifacts for a specific node/component from previous run."""
        if not self.previous_run_dir:
            return None

        try:
            element_hier_dir = hierarchy_path.replace(".", os.sep)
        except Exception as e:
            logger.error(f"Error while reloading results: element_hier_dir:{element_hier_dir}, Error: {e}")
            return

        # NOTE: Currently there us nothing to copy for components
        if is_component:
            return

        # Define source and target directories
        src_input_dir = self.previous_run_dir / element_hier_dir
        result_file = src_input_dir / "result.json"

        if src_input_dir.exists() and result_file.exists():
            with open(result_file) as f:
                _results = json.load(f)
                return _results

        return None

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

        # Add rerun information to tracing
        if self.is_rerun:
            # Modify the service name to indicate it's a rerun
            self.observability_settings.service_name = f"{self.observability_settings.service_name}-rerun"

            # Set additional tracing attributes for rerun info
            if self.previous_run_id:
                # These will be picked up by the tracing system
                os.environ["OTEL_RESOURCE_ATTRIBUTES"] = (
                    f"previous_run_id={self.previous_run_id},start_hierarchy_path={self.start_hierarchy_path},"
                )

        # Set trace file paths in settings
        self.observability_settings.trace_file_path = str(self.trace_file)
        self.observability_settings.metrics_file_path = str(self.metrics_file)
        self.observability_settings.log_file_path = str(self.log_file)

        # Use the centralized setup
        configure_observability(self.observability_settings)

        # TODO_FUTURE
        # self.initialize_observability_even_listing()

        # Log tracing info
        logger.info(f"Tracing enabled. Traces will be written to: {self.trace_file}")

    # TODO_FUTURE: Check if below is required
    def initialize_observability_even_listing(self) -> None:
        # Instrument the event bus to capture event-related spans
        original_publish = self.event_bus.publish

        async def instrumented_publish(event):
            # Get tracer
            from dhenara.agent.observability.tracing import get_tracer

            tracer = get_tracer("dhenara.dad.events")

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

    def get_resource_config(
        self,
        resource_profile="default",
    ):
        try:
            # Get resource configuration from registry
            resource_config = resource_config_registry.get(resource_profile)
            if not resource_config:
                # Fall back to creating a new one
                resource_config = self.load_default_resource_config()
                resource_config_registry.register(resource_profile, resource_config)

            return resource_config
        except Exception as e:
            raise ValueError(f"Error in resource setup: {e}")

    def load_default_resource_config(self):
        resource_config = ResourceConfig()
        resource_config.load_from_file(
            credentials_file="~/.env_keys/.dhenara_credentials.yaml",
            init_endpoints=True,
        )
        return resource_config

    def set_execution_context_caching(self, enabled: bool = True):
        """
        Enable or disable context caching to optimize memory usage.

        When disabled, only path relationships are maintained, but actual context
        objects are not stored, significantly reducing memory usage for complex flows.
        """
        self.execution_context_registry.set_caching_enabled(enabled)

    def get_dad_template_static_variables(self) -> dict:
        """Get static variables from run environment parameters."""
        # Guaranteed vars
        variables = {
            # --- Externally exposed vars
            #    1.environment variables
            "run_id": self.run_env_params.run_id,
            "run_dir": str(self.run_env_params.run_dir),
            "run_root": str(self.run_env_params.run_root),
            # --- Internal vars
            #    1. state variables
            # "_dad_trace_dir": str(self.run_env_params.trace_dir),
        }

        # Optional vars
        if self.run_env_params.outcome_repo_dir:
            variables["outcome_repo_dir"] = str(self.run_env_params.outcome_repo_dir)

        return variables
