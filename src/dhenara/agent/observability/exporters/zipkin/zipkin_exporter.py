import logging

from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def configure_zipkin_exporter(service_name, zipkin_endpoint="http://localhost:9411/api/v2/spans"):
    """Configure OpenTelemetry to export traces to Zipkin.

    Args:
        service_name: Name to identify this service in traces
        zipkin_endpoint: Zipkin collector endpoint

    Returns:
        TracerProvider configured with Zipkin exporter
    """
    # Create a resource with service info
    resource = Resource.create({"service.name": service_name})

    # Create the tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Create Zipkin exporter
    zipkin_exporter = ZipkinExporter(
        endpoint=zipkin_endpoint,
    )

    # Add Zipkin exporter to the tracer provider
    tracer_provider.add_span_processor(BatchSpanProcessor(zipkin_exporter))

    logger.info(f"Zipkin exporter configured to endpoint {zipkin_endpoint}")

    return tracer_provider
