import logging

from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def configure_jaeger_exporter(service_name, jaeger_endpoint="http://localhost:14268/api/traces"):
    """Configure OpenTelemetry to export traces to Jaeger.

    Args:
        service_name: Name to identify this service in traces
        jaeger_endpoint: Jaeger collector endpoint

    Returns:
        TracerProvider configured with Jaeger exporter
    """
    # Create a resource with service info
    resource = Resource.create({"service.name": service_name})

    # Create the tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Create Jaeger exporter
    jaeger_exporter = JaegerExporter(
        collector_endpoint=jaeger_endpoint,
    )

    # Add Jaeger exporter to the tracer provider
    tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

    logger.info(f"Jaeger exporter configured to endpoint {jaeger_endpoint}")

    return tracer_provider
