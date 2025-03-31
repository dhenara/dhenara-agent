import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar, cast

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

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


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer for the given name.

    Args:
        name: Name for the tracer (typically module name)

    Returns:
        An OpenTelemetry Tracer instance
    """
    if _tracer_provider is None:
        setup_tracing()

    return trace.get_tracer(name)


# Type variable for functions
F = TypeVar("F", bound=Callable[..., Any])


def trace_node(node_type: str) -> Callable[[F], F]:
    """Decorator to trace a node execution in Dhenara agent flows.

    Args:
        node_type: Type of node being executed

    Returns:
        Decorated function with tracing
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract node identifier from args or kwargs
            node_id = None
            if len(args) > 1:
                node_id = args[1]  # Assuming node_id is the second arg
            elif "node_id" in kwargs:
                node_id = kwargs["node_id"]

            # Get the execution context
            execution_context = None
            if len(args) > 2:
                execution_context = args[2]  # Assuming execution_context is the third arg
            elif "execution_context" in kwargs:
                execution_context = kwargs["execution_context"]

            # Create tracer
            tracer = get_tracer(f"dhenara.agent.dsl.{node_type}")

            # Start a span
            with tracer.start_as_current_span(
                f"node.{node_type}.execute",
                attributes={
                    "node.id": str(node_id) if node_id else "unknown",
                    "node.type": node_type,
                },
            ) as span:
                # Add additional context to span if available
                if execution_context and hasattr(execution_context, "current_node_identifier"):
                    span.set_attribute("node.hierarchy", execution_context.get_node_hierarchy_path())

                try:
                    # Execute the function
                    result = await func(*args, **kwargs)

                    # Record the result status in the span
                    if result is not None:
                        span.set_attribute("node.status", "success")
                    else:
                        span.set_attribute("node.status", "no_result")

                    return result
                except Exception as e:
                    # Record the error in the span
                    span.record_exception(e)
                    span.set_attribute("node.status", "error")
                    span.set_attribute("error.message", str(e))
                    raise

        return cast(F, wrapper)

    return decorator


def trace_method(name: str | None = None) -> Callable[[F], F]:
    """General purpose method decorator for tracing any method.

    Args:
        name: Optional custom name for the span

    Returns:
        Decorated method with tracing
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # Create span name from function name or provided name
            span_name = name if name else func.__name__

            # Get class name
            class_name = self.__class__.__name__

            # Create tracer
            tracer = get_tracer(f"dhenara.agent.{class_name.lower()}")

            # Start a span
            with tracer.start_as_current_span(
                f"{class_name}.{span_name}",
                attributes={
                    "class": class_name,
                    "method": func.__name__,
                },
            ) as span:
                try:
                    # Execute the function
                    result = await func(self, *args, **kwargs)
                    return result
                except Exception as e:
                    # Record the error in the span
                    span.record_exception(e)
                    span.set_attribute("error.message", str(e))
                    raise

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            # Create span name from function name or provided name
            span_name = name if name else func.__name__

            # Get class name
            class_name = self.__class__.__name__

            # Create tracer
            tracer = get_tracer(f"dhenara.agent.{class_name.lower()}")

            # Start a span
            with tracer.start_as_current_span(
                f"{class_name}.{span_name}",
                attributes={
                    "class": class_name,
                    "method": func.__name__,
                },
            ) as span:
                try:
                    # Execute the function
                    result = func(self, *args, **kwargs)
                    return result
                except Exception as e:
                    # Record the error in the span
                    span.record_exception(e)
                    span.set_attribute("error.message", str(e))
                    raise

        # Choose the appropriate wrapper based on whether the function is async or not
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator


def force_flush_tracing():
    """Force flush all pending spans to be exported."""

    # TODO:
    # If OpenTelemetry setup ever changes to use multiple span processors
    # (which is supported in the architecture),revisit below.
    if _tracer_provider:
        _tracer_provider._active_span_processor.force_flush()
        # for span_processor in _tracer_provider._span_processors:
        #    span_processor.force_flush()
