import json
import logging
from pathlib import Path
from typing import Any, Literal

from dhenara.agent.dsl.base import DADTemplateEngine, GitSettingsItem, RecordFileFormatEnum, RecordSettingsItem
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

    def _resolve_template(
        self,
        template_str: str,
        variables: dict | None = None,
        dad_dynamic_variables: dict | None = None,
    ) -> str:
        """Resolve a template string with the given variables."""
        # Handle both direct strings and TextTemplate objects
        template_text = template_str.text if hasattr(template_str, "text") else template_str
        return DADTemplateEngine.render_dad_template(
            template=template_text,
            variables=variables or {},
            dad_dynamic_variables=dad_dynamic_variables or {},
            run_env_params=self.run_env_params,
            node_execution_results=None,
            mode="standard",
        )

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

        variables = None
        dad_dynamic_variables = {
            "node_id": node_identifier,
        }

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
            path_str = self._resolve_template(record_settings.path, variables, dad_dynamic_variables)
            file_name = self._resolve_template(record_settings.filename, variables, dad_dynamic_variables)

            # Create full path - determine appropriate base directory based on record type
            base_dir = Path(self.run_env_params.run_dir)

            full_path = base_dir / path_str
            full_path.mkdir(parents=True, exist_ok=True)

            # Save data in the specified format
            output_file = full_path / file_name
            _save_file(output_file)

            # Handle git operations if git settings are provided
            if git_settings:
                # Resolve path and filename from templates
                path_str = self._resolve_template(git_settings.path, variables, dad_dynamic_variables)
                file_name = self._resolve_template(git_settings.filename, variables, dad_dynamic_variables)

                # For outcomes with git settings, use the outcome repo directory
                base_dir = Path(self.run_env_params.outcome_repo_dir)

                full_path = base_dir / path_str
                full_path.mkdir(parents=True, exist_ok=True)

                # Save data in the specified format
                output_file = full_path / file_name
                _save_file(output_file)

                if git_settings.commit:
                    commit_msg = f"{record_type.capitalize()} data recorded"
                    if git_settings.commit_message:
                        commit_msg = self._resolve_template(
                            git_settings.commit_message,
                            variables,
                            dad_dynamic_variables,
                        )
                    self.outcome_repo.commit_run_outcomes(
                        run_id=self.run_env_params.run_id,
                        message=commit_msg,
                        files=[output_file],
                    )
                elif git_settings.stage:
                    self.outcome_repo.add(output_file)

            return True
        except Exception as e:
            logger.exception(f"record_{record_type}: Error: {e}")
            return False
