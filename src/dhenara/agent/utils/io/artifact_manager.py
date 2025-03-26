import json
import logging
from datetime import datetime
from pathlib import Path
from string import Template

from dhenara.agent.dsl.base import RecordFileFormatEnum, RecordSettingsItem
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

    def _resolve_template(self, template_str: str, variables: dict) -> str:
        """Resolve a template string with the given variables."""
        # Handle both direct strings and TextTemplate objects
        template_text = template_str.text if hasattr(template_str, "text") else template_str
        return Template(template_text).safe_substitute(variables)

    def _get_template_variables(self, node_identifier: str) -> dict:
        """Get standard template variables for substitution."""
        variables = self.run_env_params.get_template_variables()
        variables.update(
            {
                "node_id": node_identifier,
                "run_id": self.run_env_params.run_id,
            }
        )
        return variables

    def record_node_input(
        self,
        node_identifier: str,
        input_data: dict,
        record_settings: RecordSettingsItem = None,
    ) -> bool:
        """Save input for a node execution."""
        if record_settings is None or not record_settings.enabled:
            return True

        variables = self._get_template_variables(node_identifier)

        try:
            # Resolve path and filename from templates
            path_str = self._resolve_template(record_settings.path, variables)
            file_name = self._resolve_template(record_settings.filename, variables)

            # Create full path
            # full_path = Path(self.run_env_params.run_dir) / path_str
            full_path = Path(path_str)
            full_path.mkdir(parents=True, exist_ok=True)

            # Save data in the specified format
            output_file = full_path / file_name
            if record_settings.file_format == RecordFileFormatEnum.json:
                with open(output_file, "w") as f:
                    json.dump(input_data, f, indent=2)
            elif record_settings.file_format == RecordFileFormatEnum.yaml:
                import yaml

                with open(output_file, "w") as f:
                    yaml.dump(input_data, f, default_flow_style=False)
            elif record_settings.file_format == RecordFileFormatEnum.text:
                with open(output_file, "w") as f:
                    f.write(str(input_data))

            # Handle git commit if enabled
            if record_settings.git_commit:
                commit_msg = "Input data recorded"
                if record_settings.git_commit_message:
                    commit_msg = self._resolve_template(record_settings.git_commit_message, variables)
                self.outcome_repo.commit_run_outcomes(self.run_env_params.run_id, commit_msg)

            return True
        except Exception as e:
            logger.exception(f"record_node_input: Error: {e}")
            return False

    def record_node_output(
        self,
        node_identifier: str,
        output_data: dict,
        record_settings: RecordSettingsItem = None,
    ) -> bool:
        """Save output from a node execution."""
        # if record_settings is None or not record_settings.enabled:
        #    # Use legacy behavior if no settings provided
        #    try:
        #        node_dir_str = f"{self.run_env_params.output_dir}/{node_identifier}"
        #        node_dir = Path(node_dir_str)
        #        node_dir.mkdir(exist_ok=True)
        #        output_file = node_dir / "node.json"
        #        with open(output_file, "w") as f:
        #            json.dump(output_data, f, indent=2)
        #        return True
        #    except Exception as e:
        #        logger.exception(f"record_node_output (legacy): Error: {e}")
        #        return False

        variables = self._get_template_variables(node_identifier)

        try:
            # Resolve path and filename from templates
            path_str = self._resolve_template(record_settings.path, variables)
            file_name = self._resolve_template(record_settings.filename, variables)

            # Create full path
            full_path = Path(self.run_env_params.run_dir) / path_str
            full_path.mkdir(parents=True, exist_ok=True)

            # Save data in the specified format
            output_file = full_path / file_name
            if record_settings.file_format == RecordFileFormatEnum.json:
                with open(output_file, "w") as f:
                    json.dump(output_data, f, indent=2)
            elif record_settings.file_format == RecordFileFormatEnum.yaml:
                import yaml

                with open(output_file, "w") as f:
                    yaml.dump(output_data, f, default_flow_style=False)
            elif record_settings.file_format == RecordFileFormatEnum.text:
                with open(output_file, "w") as f:
                    f.write(str(output_data))

            # Handle git commit if enabled
            if record_settings.git_commit:
                commit_msg = "Output data recorded"
                if record_settings.git_commit_message:
                    commit_msg = self._resolve_template(record_settings.git_commit_message, variables)
                self.outcome_repo.commit_run_outcomes(self.run_env_params.run_id, commit_msg)

            return True
        except Exception as e:
            logger.exception(f"record_node_output: Error: {e}")
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
            _file_path = Path(self.run_env_params.outcome_repo_dir) / path_in_repo
            _file_path.mkdir(parents=True, exist_ok=True)

            # Save output data
            output_file = _file_path / file_name
            with open(output_file, "w") as f:
                f.write(content)

            if commit:
                if not commit_msg:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    commit_msg = f"Outcome at {timestamp}"
                self.outcome_repo.commit_run_outcomes(
                    self.run_env_params.run_id,
                    commit_msg,
                )
            return True
        except Exception as e:
            logger.exception(f"record_outcome: Error: {e}")
            return False
