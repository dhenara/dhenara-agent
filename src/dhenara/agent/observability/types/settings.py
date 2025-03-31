import logging

from dhenara.agent.types.base import BaseModel


class ObservabilitySettings(BaseModel):
    service_name: str = "dhenara-dad"
    tracing_exporter_type: str = "file"  # "console", "file", "otlp", "jaeger"
    metrics_exporter_type: str = "file"  # "console", "file", "otlp"
    logging_exporter_type: str = "file"  # "console", "file", "otlp"
    otlp_endpoint: str | None = None
    jaeger_endpoint: str | None = "http://localhost:14268/api/traces"
    zipkin_endpoint: str | None = "http://localhost:9411/api/v2/spans"

    root_log_level: int = logging.INFO
    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    trace_file_path: str | None = None
    metrics_file_path: str | None = None
    log_file_path: str | None = None

    # For all log msgs in observability package
    observability_logger_name: str = "dhenara.agent.observability"
