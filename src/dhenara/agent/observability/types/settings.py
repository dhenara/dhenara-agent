import logging
from dataclasses import dataclass


@dataclass
class ObservabilitySettings:
    service_name: str = "dhenara-dad"
    exporter_type: str = "file"  # "console", "file", "otlp"
    otlp_endpoint: str | None = None
    trace_file_path: str | None = None
    root_log_level: int = logging.INFO
    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
