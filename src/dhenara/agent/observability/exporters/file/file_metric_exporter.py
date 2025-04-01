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

            # Append metrics to the file
            with open(self.file_path, "a") as f:
                # Handle if to_json() returns a string or a dict
                if isinstance(metric_dict, str):
                    try:
                        # If it's already a JSON string, parse it back to a dict
                        log_dict = json.loads(metric_dict)
                    except json.JSONDecodeError:
                        # If it's not a valid JSON string, just use it as is
                        f.write(log_dict + "\n")

                # Write a properly formatted JSON line with newline
                f.write(json.dumps(log_dict) + "\n")

            return MetricExportResult.SUCCESS
        except Exception as e:
            logger.error(f"Failed to export metrics to file: {e}", exc_info=True)
            return MetricExportResult.FAILURE

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shutdown the exporter."""
        pass
