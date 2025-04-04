import datetime
import json
import logging
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from dhenara.agent.dsl.base import DADTemplateEngine, GitSettingsItem, RecordFileFormatEnum, RecordSettingsItem
from dhenara.agent.types.data import RunEnvParams
from dhenara.agent.utils.git import RunOutcomeRepository

logger = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles common complex types."""

    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Path):
            return str(obj)
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return obj.to_dict()
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        return super().default(obj)


# TODO: Merge with exising
class ArtifactManagerNew:
    """
    Manager for handling data artifacts, including saving files and git operations.

    This class provides a centralized way to record data in various formats,
    with optional git integration for tracking changes.
    """

    def __init__(
        self,
        run_env_params: RunEnvParams,
        outcome_repo: RunOutcomeRepository,
    ):
        """
        Initialize the ArtifactManager.

        Args:
            run_env_params: Parameters for the run environment
            outcome_repo: Repository for managing run outcomes
        """
        self.run_env_params = run_env_params
        self.outcome_repo = outcome_repo

    @contextmanager
    def _error_context(self, operation: str):
        """
        Context manager for standardized error handling.

        Args:
            operation: Description of the operation being performed
        """
        try:
            yield
        except Exception as e:
            logger.exception(f"Error during {operation}: {e}")
            raise

    def _resolve_template(
        self,
        template_str: str,
        variables: dict[str, Any] | None = None,
        dad_dynamic_variables: dict[str, Any] | None = None,
    ) -> str:
        """
        Resolve a template string with the given variables.

        Args:
            template_str: The template string or object to resolve
            variables: Variables to use for template rendering
            dad_dynamic_variables: Dynamic variables for DAD template rendering

        Returns:
            The resolved template string
        """
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

    def _validate_data_for_format(self, data: Any, file_format: RecordFileFormatEnum) -> bool:
        """
        Validate that the data can be written in the specified format.

        Args:
            data: The data to validate
            file_format: The target format for the data

        Returns:
            True if data can be written in the specified format, False otherwise
        """
        if file_format == RecordFileFormatEnum.json:
            # Check if data is JSON serializable
            try:
                json.dumps(data, cls=CustomJSONEncoder)
                return True
            except (TypeError, OverflowError):
                return False
        elif file_format == RecordFileFormatEnum.binary:
            return isinstance(data, bytes)
        elif file_format in (RecordFileFormatEnum.yaml, RecordFileFormatEnum.text):
            # Almost anything can be converted to string or YAML
            return True
        return False

    def _write_data_to_file(
        self, data: dict[str, Any] | str | bytes, output_file: Path, file_format: RecordFileFormatEnum
    ) -> None:
        """
        Write data to file in the specified format.

        Args:
            data: The data to write
            output_file: The path to write the data to
            file_format: The format to use for writing

        Raises:
            ValueError: If the data cannot be written in the specified format
        """
        with self._error_context(f"writing data to {output_file}"):
            # Validate data for the given format
            if not self._validate_data_for_format(data, file_format):
                raise ValueError(f"Data of type {type(data)} cannot be written in {file_format} format")

            if file_format == RecordFileFormatEnum.json:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, cls=CustomJSONEncoder)
            elif file_format == RecordFileFormatEnum.yaml:
                import yaml

                with open(output_file, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False)
            elif file_format == RecordFileFormatEnum.text:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(str(data))
            elif file_format == RecordFileFormatEnum.binary:
                with open(output_file, "wb") as f:
                    f.write(data)

    def _save_to_location(
        self,
        data: dict[str, Any] | str | bytes,
        settings: RecordSettingsItem | GitSettingsItem,
        dad_dynamic_variables: dict[str, Any],
        base_dir: Path,
    ) -> Path:
        """
        Save data to the specified location and return the output file path.

        Args:
            data: The data to save
            settings: Settings containing path, filename, and format information
            dad_dynamic_variables: Dynamic variables for template resolution
            base_dir: Base directory for the file path

        Returns:
            The path to the saved file
        """
        with self._error_context(f"saving data to location {base_dir}"):
            # Resolve path and filename
            path_str = self._resolve_template(settings.path, None, dad_dynamic_variables)
            file_name = self._resolve_template(settings.filename, None, dad_dynamic_variables)

            # Create full path
            full_path = base_dir / path_str
            full_path.mkdir(parents=True, exist_ok=True)
            output_file = full_path / file_name

            # Get file format if it's a RecordSettingsItem, otherwise default to json
            file_format = getattr(settings, "file_format", RecordFileFormatEnum.json)

            # Write the data
            self._write_data_to_file(data, output_file, file_format)

            return output_file

    def _handle_git_operations(
        self, git_settings: GitSettingsItem, output_file: Path, record_type: str, dad_dynamic_variables: dict[str, Any]
    ) -> None:
        """
        Handle git operations if required.

        Args:
            git_settings: Settings for git operations
            output_file: The file to track with git
            record_type: Type of record for generating commit messages
            dad_dynamic_variables: Dynamic variables for template resolution
        """
        with self._error_context("git operations"):
            if git_settings.commit:
                commit_msg = f"{record_type.capitalize()} data recorded"
                if git_settings.commit_message:
                    commit_msg = self._resolve_template(
                        git_settings.commit_message,
                        None,
                        dad_dynamic_variables,
                    )
                self.outcome_repo.commit_run_outcomes(
                    run_id=self.run_env_params.run_id,
                    message=commit_msg,
                    files=[output_file],
                )
            elif git_settings.stage:
                self.outcome_repo.add(output_file)

    def record_data(
        self,
        dad_dynamic_variables: dict[str, Any],
        data: dict[str, Any] | str | bytes,
        record_type: Literal["input", "output", "outcome"],
        record_settings: RecordSettingsItem | None = None,
        git_settings: GitSettingsItem | None = None,
    ) -> bool:
        """
        Record data according to the specified settings.

        Args:
            dad_dynamic_variables: Dynamic variables for template resolution
            data: The data to record
            record_type: Type of record (input, output, or outcome)
            record_settings: Settings for how to record the data
            git_settings: Settings for git operations

        Returns:
            True if recording was successful, False otherwise
        """
        if record_settings is None or not record_settings.enabled:
            return True

        try:
            # Process standard file recording
            if record_settings:
                self._save_to_location(
                    data=data,
                    settings=record_settings,
                    dad_dynamic_variables=dad_dynamic_variables,
                    base_dir=Path(self.run_env_params.run_dir),
                )

            # Process git recording if applicable
            if git_settings and git_settings.enabled:
                output_file = self._save_to_location(
                    data=data,
                    settings=git_settings,
                    dad_dynamic_variables=dad_dynamic_variables,
                    base_dir=Path(self.run_env_params.outcome_repo_dir),
                )

                self._handle_git_operations(
                    git_settings=git_settings,
                    output_file=output_file,
                    record_type=record_type,
                    dad_dynamic_variables=dad_dynamic_variables,
                )

            return True
        except Exception as e:
            logger.exception(f"record_{record_type}: Error: {e}")
            return False
