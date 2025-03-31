import logging

from dhenara.agent.types.base import BaseModel


class ObservabilitySettings(BaseModel):
    service_name: str = "dhenara-dad"
    exporter_type: str = "file"  # "console", "file", "otlp"
    otlp_endpoint: str | None = None
    root_log_level: int = logging.INFO
    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    trace_file_path: str | None = None
    metrics_file_path: str | None = None
    log_file_path: str | None = None

    # For all log msgs in observability package
    observability_logger_name: str = "dhenara.agent.observability"
