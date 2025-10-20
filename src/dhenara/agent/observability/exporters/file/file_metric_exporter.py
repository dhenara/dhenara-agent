import json
import logging
from pathlib import Path

from opentelemetry.sdk.metrics import Counter, Histogram, ObservableCounter
from opentelemetry.sdk.metrics.export import AggregationTemporality, MetricExporter, MetricExportResult, MetricsData

logger = logging.getLogger(__name__)


class JsonFileMetricExporter(MetricExporter):
    """Custom exporter that writes metrics to a JSON file."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        # Don't create the file here to avoid permission issues
        if not self.file_path.exists():
            raise ValueError(
                f"File {self.file_path} does not exist. Should provide an existing file to avoid permission issues"
            )
        logger.info(f"JSON File metric exporter initialized. Writing metrics to {self.file_path}")

        super().__init__(
            preferred_temporality={
                Counter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
            }
        )

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        """Export metrics to a JSON file, one per line."""
        try:
            # Create parent directory if it doesn't exist
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert metrics data to JSON
            metric_dict = metrics_data.to_json()

            if isinstance(metric_dict, str):
                try:
                    # Provider SDK may already return a JSON string
                    log_dict = json.loads(metric_dict)
                except json.JSONDecodeError:
                    # If we cannot parse it, capture the raw string for debugging
                    log_dict = {"raw_metric_payload": metric_dict}
            else:
                log_dict = metric_dict

            # Append metrics to the file
            with open(self.file_path, "a") as f:
                f.write(json.dumps(log_dict, default=str) + "\n")

            return MetricExportResult.SUCCESS
        except Exception as e:
            logger.error(f"Failed to export metrics to file: {e}", exc_info=True)
            return MetricExportResult.FAILURE

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shutdown the exporter."""
        pass
