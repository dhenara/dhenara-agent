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
        outcome_repo: RunOutcomeRepository | None,
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

                def _json_default(o):
                    try:
                        import datetime
                        from pathlib import Path as _Path

                        if isinstance(o, _Path):
                            return str(o)
                        if isinstance(o, (set, tuple)):
                            return list(o)
                        if isinstance(o, datetime.datetime):
                            return o.isoformat()
                        if hasattr(o, "model_dump"):
                            return o.model_dump()
                        return str(o)
                    except Exception:
                        return str(o)

                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2, default=_json_default)
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

    # ------------------------------------------------------------------
    # Component & Run level helpers (always-on recording)
    # ------------------------------------------------------------------
    def record_component_result(self, execution_context: ExecutionContext, component_result: Any) -> bool:
        """Persist a component_result.json for a component (no settings needed).

        Stored under run_dir/<component_hier_path>/component_result.json
        where component_hier_path mirrors node artifact layout.
        """
        try:
            import os
            from pathlib import Path as _Path

            hier_path_fs = execution_context.get_hierarchy_path(path_joiner=os.sep, exclude_element_id=False)
            target_dir = _Path(execution_context.run_context.run_dir) / hier_path_fs
            target_dir.mkdir(parents=True, exist_ok=True)

            comp_result_file = target_dir / "component_result.json"

            def _json_default(o):
                try:
                    import datetime
                    from pathlib import Path as __Path

                    if isinstance(o, __Path):
                        return str(o)
                    if isinstance(o, (set, tuple)):
                        return list(o)
                    if isinstance(o, datetime.datetime):
                        return o.isoformat()
                    if hasattr(o, "model_dump"):
                        return o.model_dump()
                    return str(o)
                except Exception:
                    return str(o)

            data = (
                component_result.model_dump(exclude_none=True)
                if hasattr(component_result, "model_dump")
                else component_result
            )
            with open(comp_result_file, "w") as f:
                json.dump(data, f, indent=2, default=_json_default)
            return True
        except Exception as e:
            logger.debug(f"record_component_result: skipped due to error: {e}")
            return False

    # ------------------------------------------------------------------
    # Simple ad-hoc artifact dumper (callback convenience)
    # ------------------------------------------------------------------
    def record_custom_artifact(
        self,
        file_name: str,
        data: Any,
        execution_context: ExecutionContext,
        subdir: str | None = None,
    ) -> bool:
        """Persist arbitrary data produced mid-execution (eg: from a callback) into
            the component hierarchy under a dedicated 'dad-artifacts' folder.

            Layout:
                <run_dir>/<hierarchy_path>/dad-artifacts/[subdir/]<file_name>

            The format is inferred from the file extension (currently .json or .txt).
            Falls back to str() for unsupported / serialization failures.
        Returns True on (best-effort) success, False otherwise.
        """
        try:
            import datetime as _dt
            import json as _json
            import os
            from pathlib import Path as _Path

            hier_path_fs = execution_context.get_hierarchy_path(path_joiner=os.sep, exclude_element_id=False)
            target_dir = _Path(execution_context.run_context.run_dir) / hier_path_fs / "custom-artifacts"
            if subdir:
                target_dir = target_dir / subdir
            target_dir.mkdir(parents=True, exist_ok=True)

            target_file = target_dir / file_name

            # Basic serializers
            if target_file.suffix.lower() == ".json":

                def _json_default(o):
                    try:
                        if isinstance(o, (_dt.datetime, _dt.date)):
                            return o.isoformat()
                        from pathlib import Path as __Path

                        if isinstance(o, __Path):
                            return str(o)
                        if isinstance(o, (set, tuple)):
                            return list(o)
                        if hasattr(o, "model_dump"):
                            return o.model_dump()
                        return str(o)
                    except Exception:  # pragma: no cover
                        return str(o)

                with open(target_file, "w") as f:
                    _json.dump(data, f, indent=2, default=_json_default)
            else:
                # Plain text fallback
                with open(target_file, "w") as f:
                    f.write(str(data))

            logger.debug(
                "record_custom_artifact: saved %s (%s bytes)",
                target_file,
                target_file.stat().st_size if target_file.exists() else "?",
            )
            return True
        except Exception as e:  # pragma: no cover - best effort
            logger.debug(f"record_custom_artifact: skipped due to error: {e}")
            return False

    def record_run_summary(self, run_context, root_component_result: Any) -> bool:
        """Persist a run_summary.json at the run root with aggregated usage/cost."""
        try:
            from datetime import datetime as _dt

            summary = {
                "run_id": run_context.run_id,
                "execution_id": run_context.execution_id,
                "root_component_id": getattr(root_component_result, "component_id", None),
                "created_at": getattr(run_context, "created_at", None).isoformat()
                if getattr(run_context, "created_at", None)
                else None,
                "completed_at": _dt.now().isoformat(),
                "agg_usage_cost": getattr(root_component_result, "agg_usage_cost", None),
                "agg_usage_charge": getattr(root_component_result, "agg_usage_charge", None),
                "agg_usage_prompt_tokens": getattr(root_component_result, "agg_usage_prompt_tokens", None),
                "agg_usage_completion_tokens": getattr(root_component_result, "agg_usage_completion_tokens", None),
                "agg_usage_total_tokens": getattr(root_component_result, "agg_usage_total_tokens", None),
            }
            with open(run_context.run_dir / "run_summary.json", "w") as f:
                json.dump(summary, f, indent=2)
            return True
        except Exception as e:
            logger.debug(f"record_run_summary: skipped due to error: {e}")
            return False
