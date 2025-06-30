import logging
from typing import Any, Literal

from pydantic import Field, field_validator

from dhenara.agent.types.base import BaseModel

from ._log_config import LogConfig, LogLevelType


class ObservabilitySettings(BaseModel):
    service_name: str = "dhenara-dad"
    tracing_exporter_type: Literal["console", "file", "otlp", "jaeger", "zipkin"] = "file"
    metrics_exporter_type: Literal["console", "file", "otlp"] = "file"  # "console", "file", "otlp"
    logging_exporter_type: Literal["console", "file", "otlp"] = "file"  # "console", "file", "otlp"
    otlp_endpoint: str | None = None
    jaeger_endpoint: str | None = "http://localhost:14268/api/traces"
    zipkin_endpoint: str | None = "http://localhost:9411/api/v2/spans"

    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    trace_file_path: str | None = None
    metrics_file_path: str | None = None
    log_file_path: str | None = None

    # For all log msgs in observability package
    observability_logger_name: str = "dhenara.dad.observability"

    # Logging
    # TODO_FUTURE: log_config is not taken into account in dhenara-agent package. It still uses `root_log_level`
    log_config: LogConfig = Field(default_factory=LogConfig)
    stream_logs: bool = False

    # Legacy configs. TODO_FUTURE: Remove these by using log_config inside agent package
    root_log_level: LogLevelType = "INFO"  # TODO_FUTURE: Derive this from log_config
    # Configuration for log capture in traces
    trace_log_level: LogLevelType = "WARNING"  # Minimum level to include in traces

    @field_validator("root_log_level", "trace_log_level", mode="before")
    @classmethod
    def convert_legacy_log_level(cls, v: Any) -> str:
        """Convert legacy integer log levels to string format for backward compatibility."""
        if isinstance(v, int):
            # Mapping from logging module integer levels to string levels
            level_mapping = {
                logging.CRITICAL: "CRITICAL",
                logging.ERROR: "ERROR",
                logging.WARNING: "WARNING",
                logging.INFO: "INFO",
                logging.DEBUG: "DEBUG",
                logging.NOTSET: "NOTSET",
            }
            return level_mapping.get(v, "INFO")  # Default to INFO if unknown level
        return v
