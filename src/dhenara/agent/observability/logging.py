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

from dhenara.agent.observability.tracing.tracing_log_handler import TraceLogHandler
from dhenara.agent.observability.types import ObservabilitySettings

# Default service name
DEFAULT_SERVICE_NAME = "dhenara-agent"

# Global logger provider
_logger_provider = None

# Track if logging has been initialized
_logging_initialized = False


def setup_logging(settings: ObservabilitySettings) -> None:
    """Configure OpenTelemetry-integrated logging for the application."""
    global _logger_provider, _logging_initialized

    # Only initialize once
    if _logging_initialized:
        logging.getLogger(settings.observability_logger_name).debug("Logging already initialized, skipping setup")
        return

    # Create a resource with service info
    # resource = Resource.create({"service.name": settings.service_name or DEFAULT_SERVICE_NAME})
    resource = Resource(attributes={"service.name": settings.service_name or DEFAULT_SERVICE_NAME})

    # Create logger provider
    _logger_provider = LoggerProvider(resource=resource)

    # Configure the exporter
    if settings.logging_exporter_type == "otlp" and settings.otlp_endpoint:
        # Use OTLP exporter (for production use)
        log_exporter = OTLPLogExporter(endpoint=settings.otlp_endpoint)
    elif settings.logging_exporter_type == "file" and settings.log_file_path:
        from dhenara.agent.observability.exporters.file import JsonFileLogExporter

        # Use custom file exporter for logs
        log_exporter = JsonFileLogExporter(settings.log_file_path)
    else:
        # Default to console exporter (for development)
        log_exporter = ConsoleLogExporter()

    # Create and add a log processor
    _logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    # Reset root logger handlers to avoid duplication
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create a handler for the Python standard library
    handler = LoggingHandler(level=settings.root_log_level, logger_provider=_logger_provider)

    trace_handler = TraceLogHandler(level=settings.root_log_level)

    # Configure logging with these handlers
    logging.basicConfig(
        level=settings.root_log_level,
        handlers=[handler, trace_handler],
        force=True,
    )

    # Set the level on the dhenara loggers
    dhenara_logger = logging.getLogger("dhenara")
    dhenara_logger.setLevel(settings.root_log_level)

    # Mark as initialized
    _logging_initialized = True

    observability_logger = logging.getLogger(settings.observability_logger_name)
    observability_logger.setLevel(settings.root_log_level)

    observability_logger.info(
        f"Logging initialized with {settings.logging_exporter_type} exporter at level {settings.root_log_level}"
    )


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    extra_attributes: dict[str, Any] | None = None,
    exception: Exception | None = None,
) -> None:
    """Log a message with current span context information.
    Args:
        logger: Logger to use
        level: Logging level
        message: Message to log
        exception: Optional exception to include in log
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

    # Handle exception details based on severity
    exc_info = None
    if exception is not None:
        # Add basic exception info to extra attributes
        extra.update(
            {
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            }
        )

        # Include full stack trace for high severity levels
        if level >= logging.ERROR:
            exc_info = exception
            # Add additional context for critical errors
            if level >= logging.CRITICAL:
                extra.update(
                    {
                        "exception_module": getattr(exception, "__module__", "unknown"),
                        "exception_args": getattr(exception, "args", ()),
                    }
                )

        # For WARNING level, include exception class and message only
        elif level == logging.WARNING:
            # Exception info already added to extra, no stack trace needed
            pass

        # For INFO and DEBUG, minimal exception context
        else:
            # Just the basic info already added to extra
            pass

    # Log the message with the extra context
    logger.log(level, message, extra=extra, exc_info=exc_info)


def force_flush_logging():
    """Force flush all logging to be exported."""

    if _logger_provider:
        _logger_provider.force_flush()
