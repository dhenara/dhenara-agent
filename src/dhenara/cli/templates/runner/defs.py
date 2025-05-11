import logging

from dhenara.agent.observability import ObservabilitySettings
from dhenara.agent.utils.shared import find_project_root

# Set up observability with console exporter
observability_settings = ObservabilitySettings(
    service_name="main-agent-service",
    tracing_exporter_type="zipkin",  # "console", "file", "otlp", "jaeger", "zipkin"
    metrics_exporter_type="file",  # "console", "file", "otlp"
    logging_exporter_type="file",  # "console", "file", "otlp"
    root_log_level=logging.DEBUG,
    # Logs in trace data
    trace_log_level=logging.WARNING,
)


# Find project root directory
project_root = find_project_root()
if not project_root:
    print("Error: Not in a Dhenara project directory.")
