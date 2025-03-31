# src/dhenara/agent/observability/metrics.py
import logging

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from dhenara.agent.observability.exporters import JsonFileSpanExporter
from dhenara.agent.observability.types import ObservabilitySettings

# Default service name
DEFAULT_SERVICE_NAME = "dhenara-agent"

# Global meter provider
_meter_provider = None


def setup_metrics(settings: ObservabilitySettings) -> None:
    """Configure OpenTelemetry metrics for the application.

    Args:
        service_name: Name to identify this service in metrics
        exporter_type: Type of exporter to use ('console', 'otlp')
        otlp_endpoint: Endpoint URL for OTLP exporter (if otlp exporter is selected)
    """
    global _meter_provider

    # Create a resource with service info
    resource = Resource.create({"service.name": settings.service_name})

    # Configure the exporter
    if settings.exporter_type == "otlp" and settings.otlp_endpoint:
        # Use OTLP exporter (for production use)
        metric_exporter = OTLPMetricExporter(endpoint=settings.otlp_endpoint)
    elif settings.exporter_type == "file" and settings.trace_file_path:
        # Use custom file exporter
        # TODO
        metric_exporter = JsonFileSpanExporter(settings.trace_file_path)
    else:
        # Default to console exporter (for development)
        metric_exporter = ConsoleMetricExporter()

    # Create a metric reader
    metric_reader = PeriodicExportingMetricReader(metric_exporter)

    # Create and set the meter provider
    _meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(_meter_provider)

    logging.info(f"Metrics initialized with {settings.exporter_type} exporter")


def get_meter(name: str) -> metrics.Meter:
    """Get a meter for the given name.

    Args:
        name: Name for the meter (typically module name)

    Returns:
        An OpenTelemetry Meter instance
    """
    if _meter_provider is None:
        setup_metrics()

    return metrics.get_meter(name)


def record_metric(
    meter_name: str,
    metric_name: str,
    value: float,
    metric_type: str = "counter",
    attributes: dict[str, str] | None = None,
) -> None:
    """Record a metric with the specified meter.

    Args:
        meter_name: Name of the meter
        metric_name: Name of the metric
        value: Value to record
        metric_type: Type of metric ('counter', 'gauge', 'histogram')
        attributes: Optional attributes to associate with the metric
    """
    meter = get_meter(meter_name)

    # Create attributes dict if None
    attributes = attributes or {}

    # Record the metric based on type
    if metric_type == "counter":
        counter = meter.create_counter(name=metric_name)
        counter.add(value, attributes)
    elif metric_type == "gauge":
        # OpenTelemetry Python SDK doesn't have direct gauge support
        # Use observable gauge or updown counter instead
        up_down_counter = meter.create_up_down_counter(name=metric_name)
        up_down_counter.add(value, attributes)
    elif metric_type == "histogram":
        histogram = meter.create_histogram(name=metric_name)
        histogram.record(value, attributes)
    else:
        logging.warning(f"Unknown metric type: {metric_type}")
