import logging
from collections.abc import Callable
from typing import Any, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import format_trace_id

from dhenara.agent.observability.types import ObservabilitySettings

# Default service name
DEFAULT_SERVICE_NAME = "dhenara-dad"

# Configure tracer provider
_tracer_provider = None


def setup_tracing(settings: ObservabilitySettings) -> None:
    """Configure OpenTelemetry tracing for the application.

    Args:
        service_name: Name to identify this service in traces
        exporter_type: Type of exporter to use ('console', 'file', 'otlp')
        otlp_endpoint: Endpoint URL for OTLP exporter (if otlp exporter is selected)
        trace_file_path: Path to write traces (if file exporter is selected)
    """
    global _tracer_provider

    # Create a resource with service info
    resource = Resource.create({"service.name": settings.service_name})

    # Create the tracer provider
    _tracer_provider = TracerProvider(resource=resource)

    # Configure the exporter
    # In the setup_tracing function
    if settings.tracing_exporter_type == "jaeger" and settings.jaeger_endpoint:
        from dhenara.agent.observability.exporters.jaeger import configure_jaeger_exporter

        _tracer_provider = configure_jaeger_exporter(
            service_name=settings.service_name, jaeger_endpoint=settings.jaeger_endpoint
        )

    elif settings.tracing_exporter_type == "zipkin" and settings.zipkin_endpoint:
        from dhenara.agent.observability.exporters.zipkin import configure_zipkin_exporter

        _tracer_provider = configure_zipkin_exporter(
            service_name=settings.service_name, zipkin_endpoint=settings.zipkin_endpoint
        )

    elif settings.tracing_exporter_type == "otlp" and settings.otlp_endpoint:
        # Use OTLP exporter (for production use)
        span_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        # Create tracing processor
        _tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    elif settings.tracing_exporter_type == "file" and settings.trace_file_path:
        from dhenara.agent.observability.exporters.file import JsonFileSpanExporter

        # Use custom file exporter
        span_exporter = JsonFileSpanExporter(settings.trace_file_path)
        # Create tracing processor
        _tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    else:
        # Default to console exporter (for development)
        span_exporter = ConsoleSpanExporter()
        # Create tracing processor
        _tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))

    # Set the global tracer provider
    trace.set_tracer_provider(_tracer_provider)
    logging.info(f"Tracing initialized with {settings.tracing_exporter_type} exporter")


def is_tracing_disabled() -> trace.Tracer:
    """
    Check whether tracing profile is not availabel
    """
    return True if _tracer_provider is None else None


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer for the given name.

    Args:
        name: Name for the tracer (typically module name)

    Returns:
        An OpenTelemetry Tracer instance
    """
    if is_tracing_disabled():
        # setup_tracing()
        return None

    return trace.get_tracer(name)


# Type variable for functions
F = TypeVar("F", bound=Callable[..., Any])


def force_flush_tracing():
    """Force flush all pending spans to be exported."""

    # TODO_FUTURE:
    # If OpenTelemetry setup ever changes to use multiple span processors
    # (which is supported in the architecture),revisit below.
    if _tracer_provider:
        _tracer_provider._active_span_processor.force_flush()
        # for span_processor in _tracer_provider._span_processors:
        #    span_processor.force_flush()


def get_current_trace_id():
    # Get the current active span
    current_span = trace.get_current_span()

    if current_span != trace.INVALID_SPAN:
        # Get the span context
        span_context = current_span.get_span_context()

        # Get trace ID as hex string
        trace_id_hex = format_trace_id(span_context.trace_id)
        return trace_id_hex

    return None
