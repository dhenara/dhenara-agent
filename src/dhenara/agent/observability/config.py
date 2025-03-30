# src/dhenara/agent/observability/config.py
import logging
import os

from .logging import setup_logging
from .metrics import setup_metrics
from .tracing import setup_tracing


def configure_observability(
    service_name: str = "dhenara-agent",
    exporter_type: str = "console",
    otlp_endpoint: str | None = None,
    logging_level: int = logging.INFO,
    enable_tracing: bool = True,
    enable_metrics: bool = True,
    enable_logging: bool = True,
) -> None:
    """Configure all observability components with consistent settings.

    Args:
        service_name: Name to identify this service
        exporter_type: Type of exporter to use ('console', 'otlp')
        otlp_endpoint: Endpoint URL for OTLP exporter
        logging_level: Log level for the root logger
        enable_tracing: Whether to enable tracing
        enable_metrics: Whether to enable metrics
        enable_logging: Whether to enable enhanced logging
    """
    # Read from environment if not provided
    if not otlp_endpoint:
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    if enable_tracing:
        setup_tracing(service_name, exporter_type, otlp_endpoint)

    if enable_metrics:
        setup_metrics(service_name, exporter_type, otlp_endpoint)

    if enable_logging:
        setup_logging(service_name, exporter_type, otlp_endpoint, logging_level)

    logging.info(f"Observability configured for service {service_name} using {exporter_type} exporter")


def load_config_from_file(config_file: str) -> dict:
    """Load observability configuration from a file.

    Args:
        config_file: Path to YAML or JSON configuration file

    Returns:
        Dict containing configuration values
    """
    import json

    import yaml

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file {config_file} not found")

    if config_file.endswith(".json"):
        with open(config_file) as f:
            return json.load(f)
    elif config_file.endswith((".yml", ".yaml")):
        with open(config_file) as f:
            return yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported configuration file format: {config_file}")
