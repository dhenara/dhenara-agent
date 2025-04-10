import json
import os
from datetime import datetime


class ConsoleTraceViewer:
    """Simple console-based viewer for trace data from the console exporter."""

    def __init__(self, trace_file: str):
        """Initialize the trace viewer.

        Args:
            trace_file: Path to the trace JSON file
        """
        self.trace_file = trace_file
        self.traces = []
        self._load_traces()

    def _load_traces(self) -> None:
        """Load traces from the file."""
        if not os.path.exists(self.trace_file):
            raise FileNotFoundError(f"Trace file {self.trace_file} not found")

        with open(self.trace_file) as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    try:
                        trace_data = json.loads(line)
                        self.traces.append(trace_data)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON: {e}")

    def print_summary(self) -> None:
        """Print a summary of the traces."""
        if not self.traces:
            print("No traces found.")
            return

        print(f"Found {len(self.traces)} spans")

        # Group spans by trace ID
        trace_groups = {}
        for span in self.traces:
            trace_id = span.get("trace_id")
            if trace_id not in trace_groups:
                trace_groups[trace_id] = []
            trace_groups[trace_id].append(span)

        print(f"Found {len(trace_groups)} traces")

        # Print summary for each trace
        for trace_id, spans in trace_groups.items():
            root_spans = [s for s in spans if s.get("parent_id") is None]
            if root_spans:
                root_span = root_spans[0]
                start_time = datetime.fromtimestamp(root_span.get("start_time", 0) / 1e9)
                print(f"\nTrace {trace_id} - {start_time}")
                print(f"  Root span: {root_span.get('name')}")
                print(f"  Total spans: {len(spans)}")

    def print_trace(self, trace_id: str) -> None:
        """Print details for a specific trace.

        Args:
            trace_id: ID of the trace to print
        """
        # Filter spans by trace ID
        spans = [s for s in self.traces if s.get("trace_id") == trace_id]

        if not spans:
            print(f"No trace found with ID {trace_id}")
            return

        # Sort spans by start time
        spans.sort(key=lambda s: s.get("start_time", 0))

        # Create a span hierarchy
        span_map = {s.get("span_id"): s for s in spans}  # noqa: F841
        hierarchy = {}

        for span in spans:
            parent_id = span.get("parent_id")
            span_id = span.get("span_id")

            if parent_id is None:
                # Root span
                hierarchy[span_id] = {"span": span, "children": {}}
            else:
                # Find parent in hierarchy
                parent = None
                for root in hierarchy.values():
                    if self._find_parent(root, parent_id, span_id, span):
                        parent = True
                        break

                # If parent not found, add as root (this shouldn't happen with valid traces)
                if parent is None:
                    hierarchy[span_id] = {"span": span, "children": {}}

        # Print the hierarchy
        for _root_id, root in hierarchy.items():  # noqa: PERF102
            self._print_span_tree(root, 0)

    def _find_parent(self, node: dict, parent_id: str, span_id: str, span: dict) -> bool:
        """Recursively find a parent in the hierarchy and add the child.

        Args:
            node: Current node in the hierarchy
            parent_id: ID of the parent to find
            span_id: ID of the span to add
            span: Span data to add

        Returns:
            True if parent was found and child added, False otherwise
        """
        if node["span"].get("span_id") == parent_id:
            node["children"][span_id] = {"span": span, "children": {}}
            return True

        for child in node["children"].values():
            if self._find_parent(child, parent_id, span_id, span):
                return True

        return False

    def _print_span_tree(self, node: dict, depth: int) -> None:
        """Recursively print a span tree.

        Args:
            node: Node in the span hierarchy
            depth: Current depth in the tree
        """
        span = node["span"]
        indent = "  " * depth

        name = span.get("name", "unknown")
        start_time = datetime.fromtimestamp(span.get("start_time", 0) / 1e9)
        end_time = datetime.fromtimestamp(span.get("end_time", 0) / 1e9)
        duration_ms = (end_time - start_time).total_seconds() * 1000

        print(f"{indent}{name} - {duration_ms:.2f}ms")

        # Print attributes
        if "attributes" in span:
            for key, value in span["attributes"].items():
                print(f"{indent}  {key}: {value}")

        # Print children
        for child in node["children"].values():
            self._print_span_tree(child, depth + 1)


def view_trace_in_console(file, trace_id: str | None = None):
    """Command-line interface for the console trace viewer."""

    try:
        viewer = ConsoleTraceViewer(file)

        if trace_id:
            viewer.print_trace(trace_id)
        else:
            viewer.print_summary()
    except Exception as e:
        print(f"Error viewing traces: {e}")
