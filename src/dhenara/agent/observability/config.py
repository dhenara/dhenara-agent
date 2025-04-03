# src/dhenara/agent/observability/config.py
import logging
import os

from dhenara.agent.observability.types import ObservabilitySettings

from .logging import setup_logging
from .metrics import setup_metrics
from .tracing import setup_tracing

_current_settings: ObservabilitySettings = None


def configure_observability(settings: ObservabilitySettings) -> None:
    """Configure all observability components with consistent settings."""
    global _current_settings
    _current_settings = settings

    # Read from environment if not provided
    if not settings.otlp_endpoint:
        settings.otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    # Configure components in order: logging first, then tracing, then metrics
    if settings.enable_logging:
        setup_logging(settings)

    if settings.enable_tracing:
        setup_tracing(settings)

    if settings.enable_metrics:
        setup_metrics(settings)

    logger = logging.getLogger(settings.observability_logger_name)
    logger.info(f"Observability configured for {settings.service_name} using {settings.logging_exporter_type} exporter")


def get_current_settings() -> ObservabilitySettings:
    """Get the current observability settings."""
    global _current_settings
    if _current_settings is None:
        # Return default settings if not configured
        _current_settings = ObservabilitySettings()
        logger = logging.getLogger(_current_settings.observability_logger_name)
        logger.warning(
            "Using default settings for observability as it was not configured. "
            "Use `configure_observability()` to set it with your preference"
        )

    return _current_settings
