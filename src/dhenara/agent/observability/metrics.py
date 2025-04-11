# src/dhenara/agent/observability/metrics.py
import logging

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from dhenara.agent.observability.types import ObservabilitySettings

# Default service name
DEFAULT_SERVICE_NAME = "dhenara-agent"

# Global meter provider
_meter_provider = None


def setup_metrics(settings: ObservabilitySettings) -> None:
    """Configure OpenTelemetry metrics for the application.

    Args:
        settings: Observability settings containing configuration details
    """
    global _meter_provider

    # If metrics are already set up, don't reinitialize
    if _meter_provider is not None:
        logging.getLogger(settings.observability_logger_name).debug("Metrics already initialized, skipping setup")
        return

    # Create a resource with service info
    resource = Resource.create({"service.name": settings.service_name})

    # Configure metric readers and exporters
    metric_readers = []

    try:
        if settings.metrics_exporter_type == "otlp" and settings.otlp_endpoint:
            # Use OTLP exporter (for production use)
            metric_exporter = OTLPMetricExporter(endpoint=settings.otlp_endpoint)
            metric_readers.append(PeriodicExportingMetricReader(metric_exporter))
        elif settings.metrics_exporter_type == "file" and settings.metrics_file_path:
            from dhenara.agent.observability.exporters.file import JsonFileMetricExporter

            # Use custom file exporter
            metric_exporter = JsonFileMetricExporter(settings.metrics_file_path)
            metric_readers.append(PeriodicExportingMetricReader(metric_exporter))
        else:
            # Default to console exporter (for development)
            metric_exporter = ConsoleMetricExporter()
            metric_readers.append(PeriodicExportingMetricReader(metric_exporter))

        # Create and set the meter provider
        _meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
        metrics.set_meter_provider(_meter_provider)

        logging.getLogger(settings.observability_logger_name).info(
            f"Metrics initialized with {settings.metrics_exporter_type} exporter"
        )
    except Exception as e:
        # Add robust error handling so metrics issues don't crash the application
        logger = logging.getLogger(settings.observability_logger_name)
        logger.error(f"Failed to set up metrics: {e}", exc_info=True)

        # Set up a basic provider so the rest of the app can continue
        _meter_provider = MeterProvider(resource=resource)
        metrics.set_meter_provider(_meter_provider)

        logger.info("Falling back to default metrics provider due to setup error")


def get_meter(name: str) -> metrics.Meter:
    """Get a meter for the given name.

    Args:
        name: Name for the meter (typically module name)

    Returns:
        An OpenTelemetry Meter instance
    """
    # We should check if setup has been done, but don't initialize here
    if _meter_provider is None:
        logging.getLogger("dhenara.dad.observability").warning(
            "Attempting to get meter before metrics initialization. "
            "Metrics will not be recorded until setup_metrics() is called."
        )
        # Return a no-op meter instead of setting up metrics
        return metrics.get_meter(name)

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

    if _meter_provider is None:
        logging.getLogger("dhenara.dad.observability").debug(
            f"Skipping metric recording for {metric_name}: metrics not initialized"
        )
        return

    meter = get_meter(meter_name)

    # Create attributes dict if None
    attributes = attributes or {}

    # Record the metric based on type
    try:
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
            logging.getLogger("dhenara.dad.observability").warning(f"Unknown metric type: {metric_type}")
    except Exception as e:
        logging.getLogger("dhenara.dad.observability").error(
            f"Error recording metric {metric_name}: {e}", exc_info=True
        )


def force_flush_metrics():
    """Force flush all metrics to be exported."""

    if _meter_provider:
        _meter_provider.force_flush()
