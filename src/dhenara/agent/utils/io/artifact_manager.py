import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from dhenara.agent.dsl.base import DADTemplateEngine, RecordFileFormatEnum, RecordSettingsItem
from dhenara.agent.types.data import RunEnvParams
from dhenara.agent.utils.git import RunOutcomeRepository

if TYPE_CHECKING:
    from dhenara.agent.dsl.base import ExecutionContext
else:
    ExecutionContext = Any

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
        variables: dict | None,
        execution_context: ExecutionContext,
    ) -> str:
        """Resolve a template string with the given variables."""
        # Handle both direct strings and TextTemplate objects
        template_text = template_str.text if hasattr(template_str, "text") else template_str
        return DADTemplateEngine.render_dad_template(
            template=template_text,
            variables=variables or {},
            execution_context=execution_context,
            mode="standard",  # NOTE: Standard mode. No $expr() are allowed
        )

    def record_data(
        self,
        record_type: Literal["state", "outcome", "result", "file"],
        data: dict | str | bytes,
        record_settings: RecordSettingsItem | None,
        execution_context: ExecutionContext,
    ) -> bool:
        """Common implementation for recording node data."""
        if record_settings is None or not record_settings.enabled:
            return True

        variables = None

        # TODO_FUTURE: Do data type checks
        def _save_file(output_file):
            # Save data in the specified format
            if record_settings.file_format == RecordFileFormatEnum.json:
                if not isinstance(data, (dict, list)):
                    logger.error(f"Cannot save data as JSON: expected dict or list, got {type(data)}")
                    # return False

                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
            elif record_settings.file_format == RecordFileFormatEnum.yaml:
                import yaml

                if not isinstance(data, (dict, list)):
                    logger.error(f"Cannot save data as YAML: expected dict or list, got {type(data)}")
                    # return False

                with open(output_file, "w") as f:
                    yaml.dump(data, f, default_flow_style=False)
            elif record_settings.file_format == RecordFileFormatEnum.text:
                with open(output_file, "w") as f:
                    f.write(str(data))
            elif record_settings.file_format == RecordFileFormatEnum.binary:
                if not isinstance(data, bytes):
                    logger.error(f"Cannot save data as binary/image: expected bytes, got {type(data)}")
                    # return False

                with open(output_file, "wb") as f:
                    f.write(data)

            elif record_settings.file_format == RecordFileFormatEnum.image:
                import io

                from PIL import Image

                if not isinstance(data, bytes):
                    logger.error(f"Cannot save data as binary/image: expected bytes, got {type(data)}")
                    # return False

                image = Image.open(io.BytesIO(data))
                # Using the already opened file handle "f"
                with open(output_file, "wb") as f:
                    image.save(f, format="PNG")

            return True

        try:
            # Resolve path and filename from templates
            path_str = self._resolve_template(record_settings.path, variables, execution_context)
            file_name = self._resolve_template(record_settings.filename, variables, execution_context)

            # Create full path - determine appropriate base directory based on record type
            base_dir = Path(self.run_env_params.run_dir)

            full_path = base_dir / path_str
            full_path.mkdir(parents=True, exist_ok=True)

            # Save data in the specified format
            output_file = full_path / file_name
            _save_file(output_file)

            return True
        except Exception as e:
            logger.exception(f"record_{record_type}: Error: {e}")
            return False
