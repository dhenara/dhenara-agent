import json
import logging
from collections.abc import Sequence
from pathlib import Path

from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult

logger = logging.getLogger(__name__)


class JsonFileLogExporter(LogExporter):
    """Custom exporter that writes logs to a JSON file."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        # Don't create the file here to avoid permission issues
        if not self.file_path.exists():
            raise ValueError(
                f"File {self.file_path} does not exist. Should provide an existing file to avoid permission issues"
            )
        logger.info(f"JSON File log exporter initialized. Writing logs to {self.file_path}")

    def export(self, batch: Sequence[LogData]) -> LogExportResult:  # Changed parameter type to LogData
        """Export logs to a JSON file, one per line."""

        try:
            # Create parent directory if it doesn't exist
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Append logs to the file
            with open(self.file_path, "a", encoding="utf-8") as f:
                for log_data in batch:
                    # Convert log record to a dict and then to a JSON string
                    log_dict = log_data.log_record.to_json()

                    # Handle if to_json() returns a string or a dict
                    if isinstance(log_dict, str):
                        try:
                            # If it's already a JSON string, parse it back to a dict
                            log_dict = json.loads(log_dict)
                        except json.JSONDecodeError:
                            # If it's not a valid JSON string, just use it as is
                            f.write(log_dict + "\n")
                            continue

                    # Write a properly formatted JSON line with newline
                    f.write(json.dumps(log_dict) + "\n")

            return LogExportResult.SUCCESS
        except Exception as e:
            logger.error(f"Failed to export logs to file: {e}", exc_info=True)
            return LogExportResult.FAILURE

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        pass
