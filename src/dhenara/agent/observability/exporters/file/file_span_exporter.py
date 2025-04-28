import json
import logging
from collections.abc import Sequence
from pathlib import Path

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)


class JsonFileSpanExporter(SpanExporter):
    """Custom exporter that writes spans to a JSON file."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

        # NOTE: Do not create file here, as it will create permisson issues especially with Isolated Runs
        # Create the directory if it doesn't exist
        # self.file_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.file_path.exists():
            raise ValueError(
                f"File {self.file_path} does not exists. Should provide an existing file to avoid permission issues"
            )
        logger.info(f"JSON File exporter initialized. Writing traces to {self.file_path}")

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans to a JSON file, one per line."""
        try:
            # Create parent directory if it doesn't exist
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Append spans to the file
            with open(self.file_path, "a", encoding="utf-8") as f:
                for span in spans:
                    # Convert span record to a dict and then to a JSON string
                    span_dict = span.to_json()

                    # Handle if to_json() returns a string or a dict
                    if isinstance(span_dict, str):
                        try:
                            # If it's already a JSON string, parse it back to a dict
                            span_dict = json.loads(span_dict)
                        except json.JSONDecodeError:
                            # If it's not a valid JSON string, just use it as is
                            f.write(span_dict + "\n")
                            continue

                    # Write a properly formatted JSON line with newline
                    f.write(json.dumps(span_dict) + "\n")

            return SpanExportResult.SUCCESS
        except Exception as e:
            logger.error(f"Failed to export spans to file: {e}", exc_info=True)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        pass
