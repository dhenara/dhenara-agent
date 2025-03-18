import json
import logging
from pathlib import Path

from dhenara.agent.types.data import RunEnvParams
from dhenara.agent.utils.git import RunOutcomeRepository

logger = logging.getLogger(__name__)


class ArtifactManager:
    def __init__(
        self,
        run_env_params: RunEnvParams,
        outcome_repo: RunOutcomeRepository,
    ):
        self.run_env_params = run_env_params
        self.outcome_repo = outcome_repo

    def record_node_output(
        self,
        node_identifier,
        output_file_name,
        output_data,
    ):
        """Save output from a node execution."""
        try:
            # Create node output directory
            node_dir_str = f"{self.run_env_params.output_dir}/{node_identifier}"

            node_dir = Path(node_dir_str)
            node_dir.mkdir(exist_ok=True)

            output_file = node_dir / output_file_name
            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2)
        except Exception as e:
            logger.exception(f"emit_node_output: Error: {e}")
            return False

    def record_outcome(
        self,
        file_name,
        path_in_repo,
        content,
        commit=True,
        commit_msg=None,
    ):
        """Save an outcome file into the repo."""
        try:
            _file_path = self.run_env_params.output_repo / path_in_repo
            _file_path.mkdir(parents=True, exist_ok=True)

            # # Save output data
            output_file = _file_path / file_name
            with open(output_file, "w") as f:
                f.write(content)

            if commit:
                if not commit_msg:
                    timestamp = self.run_env_params._get_timestamp_str()
                    commit_msg = f"Outcome at {timestamp}"

                self.run_env_params.output_repo.commit_run_outputs(
                    self.run_env_params.run_id,
                    commit_msg,
                )

            return True
        except Exception as e:
            logger.exception(f"emit_outcome: Error: {e}")
            return False
