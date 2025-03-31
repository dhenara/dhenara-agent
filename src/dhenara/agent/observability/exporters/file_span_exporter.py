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
            with open(self.file_path, "a") as f:
                for span in spans:
                    # Convert span to JSON-serializable dict
                    span_json = self._span_to_json(span)
                    # Write as a single line
                    f.write(json.dumps(span_json) + "\n")
                    print(f"AJ: export : span={span}")

            return SpanExportResult.SUCCESS
        except Exception as e:
            logger.error(f"Failed to export spans to file: {e}", exc_info=True)
            return SpanExportResult.FAILURE

    def _span_to_json(self, span: ReadableSpan) -> dict:
        """Convert a span to a JSON-serializable dict."""
        context = span.get_span_context()
        # Basic span data
        span_json = {
            "name": span.name,
            "context": {
                "trace_id": format(context.trace_id, "032x"),
                "span_id": format(context.span_id, "016x"),
                "trace_state": f"{context.trace_state}",
            },
            "kind": f"{span.kind}",
            "parent_id": format(span.parent.span_id, "016x") if span.parent else None,
            "start_time": span.start_time.isoformat() if hasattr(span.start_time, "isoformat") else span.start_time,
            "end_time": span.end_time.isoformat() if hasattr(span.end_time, "isoformat") else span.end_time,
            "status": {
                "status_code": f"{span.status.status_code.name}"
                if hasattr(span.status.status_code, "name")
                else f"{span.status.status_code}",
                "description": span.status.description,
            },
            "attributes": dict(span.attributes),
            "events": [
                {
                    "name": event.name,
                    "timestamp": event.timestamp,
                    "attributes": dict(event.attributes),
                }
                for event in span.events
            ],
            "links": [],
            "resource": {
                "attributes": dict(span.resource.attributes),
                "schema_url": span.resource.schema_url,
            },
        }
        return span_json

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        pass
