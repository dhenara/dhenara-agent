# src/dhenara/agent/observability/logging.py
import logging
from typing import Any

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import (
    LoggerProvider,
    LoggingHandler,
)
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    ConsoleLogExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import get_current_span

# Default service name
DEFAULT_SERVICE_NAME = "dhenara-agent"

# Global logger provider
_logger_provider = None


def setup_logging(
    service_name: str = DEFAULT_SERVICE_NAME,
    exporter_type: str = "console",
    otlp_endpoint: str | None = None,
    root_log_level: int = logging.INFO,
) -> None:
    """Configure OpenTelemetry-integrated logging for the application.

    Args:
        service_name: Name to identify this service in logs
        exporter_type: Type of exporter to use ('console', 'otlp')
        otlp_endpoint: Endpoint URL for OTLP exporter (if otlp exporter is selected)
        root_log_level: Log level for the root logger
    """
    global _logger_provider

    # Create a resource with service info
    resource = Resource.create({"service.name": service_name})

    # Create logger provider
    _logger_provider = LoggerProvider(resource=resource)

    # Configure the exporter
    if exporter_type == "otlp" and otlp_endpoint:
        # Use OTLP exporter (for production use)
        log_exporter = OTLPLogExporter(endpoint=otlp_endpoint)
    else:
        # Default to console exporter (for development)
        log_exporter = ConsoleLogExporter()

    # Create and add a log processor
    _logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    # Create a handler for the Python standard library
    handler = LoggingHandler(level=root_log_level, logger_provider=_logger_provider)

    # Configure logging with this handler
    logging.basicConfig(level=root_log_level, handlers=[handler])

    # Also set the handler on the root logger to make sure it's available
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    # Set the level on the dhenara loggers
    logging.getLogger("dhenara").setLevel(root_log_level)

    logging.info(f"Logging initialized with {exporter_type} exporter")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Name for the logger (typically module name)

    Returns:
        A standard logging.Logger instance configured with OpenTelemetry
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    extra_attributes: dict[str, Any] | None = None,
) -> None:
    """Log a message with current span context information.

    Args:
        logger: Logger to use
        level: Logging level
        message: Message to log
        extra_attributes: Optional extra attributes to include in log
    """
    # Get the current span
    span = get_current_span()

    # Prepare extra context
    extra = extra_attributes or {}

    # Add trace context if available
    if span.is_recording():
        span_context = span.get_span_context()
        extra.update(
            {
                "trace_id": format(span_context.trace_id, "032x"),
                "span_id": format(span_context.span_id, "016x"),
            }
        )

    # Log the message with the extra context
    logger.log(level, message, extra=extra)
