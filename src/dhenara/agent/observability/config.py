# src/dhenara/agent/observability/config.py
import logging

from dhenara.agent.observability.types import ObservabilitySettings

from .logging import setup_logging
from .metrics import setup_metrics
from .tracing import setup_tracing


def configure_observability(settings: ObservabilitySettings) -> None:
    """Configure all observability components with consistent settings."""
    # Read from environment if not provided
    # if not settings.otlp_endpoint:
    #    settings.otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    # Configure components in order: logging first, then tracing, then metrics
    if settings.enable_logging:
        setup_logging(settings)

    if settings.enable_tracing:
        setup_tracing(settings)

    if settings.enable_metrics:
        setup_metrics(settings)

    logger = logging.getLogger("dhenara.agent.observability")
    logger.info(f"Observability configured for {settings.service_name} using {settings.exporter_type} exporter")
