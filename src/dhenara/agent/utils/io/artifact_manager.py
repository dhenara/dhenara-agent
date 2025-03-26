import json
import logging
from pathlib import Path
from string import Template
from typing import Any, Literal

from dhenara.agent.dsl.base import GitSettingsItem, RecordFileFormatEnum, RecordSettingsItem
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

    def record_data(
        self,
        node_identifier: str,
        data: Any,
        record_type: Literal["input", "output", "outcome"],
        record_settings: RecordSettingsItem = None,
        git_settings: GitSettingsItem = None,
    ) -> bool:
        """Common implementation for recording node data."""
        if record_settings is None or not record_settings.enabled:
            return True

        variables = self._get_template_variables(node_identifier)

        def _save_file(output_file):
            # Save data in the specified format
            if record_settings.file_format == RecordFileFormatEnum.json:
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
            elif record_settings.file_format == RecordFileFormatEnum.yaml:
                import yaml

                with open(output_file, "w") as f:
                    yaml.dump(data, f, default_flow_style=False)
            elif record_settings.file_format == RecordFileFormatEnum.text:
                with open(output_file, "w") as f:
                    f.write(str(data))
            elif record_settings.file_format == RecordFileFormatEnum.binary:
                with open(output_file, "wb") as f:
                    f.write(data)

        try:
            # Resolve path and filename from templates
            path_str = self._resolve_template(record_settings.path, variables)
            file_name = self._resolve_template(record_settings.filename, variables)

            # Create full path - determine appropriate base directory based on record type
            base_dir = Path(self.run_env_params.run_dir)

            full_path = base_dir / path_str
            full_path.mkdir(parents=True, exist_ok=True)

            # Save data in the specified format
            output_file = full_path / file_name
            _save_file(output_file)

            # Handle git operations if git settings are provided
            if git_settings and git_settings.commit:
                # Resolve path and filename from templates
                path_str = self._resolve_template(git_settings.path, variables)
                file_name = self._resolve_template(git_settings.filename, variables)

                # For outcomes with git settings, use the outcome repo directory
                base_dir = Path(self.run_env_params.outcome_repo_dir)

                full_path = base_dir / path_str
                full_path.mkdir(parents=True, exist_ok=True)

                # Save data in the specified format
                output_file = full_path / file_name
                _save_file(output_file)

                commit_msg = f"{record_type.capitalize()} data recorded"
                if git_settings.commit_message:
                    commit_msg = self._resolve_template(git_settings.commit_message, variables)
                self.outcome_repo.commit_run_outcomes(self.run_env_params.run_id, commit_msg)

            return True
        except Exception as e:
            logger.exception(f"record_{record_type}: Error: {e}")
            return False

    '''
    def record_node_input(
        self,
        node_identifier: str,
        input_data: Any,
        record_settings: RecordSettingsItem = None,
        git_settings: GitSettingsItem = None,
    ) -> bool:
        """Save input for a node execution."""
        return self._record_data(
            node_identifier=node_identifier,
            data=input_data,
            record_type="input",
            record_settings=record_settings,
            git_settings=git_settings,
        )

    def record_node_output(
        self,
        node_identifier: str,
        output_data: Any,
        record_settings: RecordSettingsItem = None,
        git_settings: GitSettingsItem = None,
    ) -> bool:
        """Save output from a node execution."""
        return self._record_data(
            node_identifier=node_identifier,
            data=output_data,
            record_type="output",
            record_settings=record_settings,
            git_settings=git_settings,
        )

    def record_outcome(
        self,
        node_identifier: str,
        outcome_data: Any,
        record_settings: RecordSettingsItem = None,
        git_settings: GitSettingsItem = None,
    ) -> bool:
        """Save an outcome file into the repo."""
        return self._record_data(
            node_identifier=node_identifier,
            data=outcome_data,
            record_type="outcome",
            record_settings=record_settings,
            git_settings=git_settings,
        )

    '''
