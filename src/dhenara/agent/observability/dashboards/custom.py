import argparse
import http.server
import json
import os
import socketserver
import webbrowser
from datetime import datetime
from typing import Any


class TraceData:
    """Class to manage and process trace data."""

    def __init__(self, trace_file: str | None = None):
        """Initialize with optional trace file."""
        self.trace_file = trace_file
        self.traces = []
        if trace_file:
            self._load_from_file(trace_file)

    def _load_from_file(self, file_path: str) -> None:
        """Load traces from a file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Trace file {file_path} not found")

        with open(file_path) as f:
            for line in f:
                try:
                    trace_data = json.loads(line.strip())
                    self.traces.append(trace_data)
                except json.JSONDecodeError:  # noqa: PERF203
                    continue

    def get_traces(self) -> list[dict[str, Any]]:
        """Get all loaded traces."""
        return self.traces

    def get_trace_ids(self) -> list[str]:
        """Get all unique trace IDs."""
        trace_ids = set()
        for trace in self.traces:
            # Check direct trace_id
            if "trace_id" in trace:
                trace_ids.add(trace["trace_id"])
            # Check trace_id in context
            elif "context" in trace and "trace_id" in trace["context"]:
                trace_ids.add(trace["context"]["trace_id"])
        return list(trace_ids)

    def get_spans_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        """Get all spans for a specific trace ID."""
        matching_spans = []
        for trace in self.traces:
            # Check direct trace_id
            if trace.get("trace_id") == trace_id:
                matching_spans.append(trace)
            # Check trace_id in context
            elif "context" in trace and trace["context"].get("trace_id") == trace_id:
                matching_spans.append(trace)
        return matching_spans

    def get_trace_summary(self) -> list[dict[str, Any]]:
        """Get a summary of all traces."""
        trace_ids = self.get_trace_ids()
        summaries = []

        for trace_id in trace_ids:
            spans = self.get_spans_for_trace(trace_id)
            # Find root spans - those with no parent_id
            root_spans = [s for s in spans if s.get("parent_id") is None]

            if root_spans:
                root_span = root_spans[0]
                # Convert nanoseconds to seconds for timestamps
                start_time = root_span.get("start_time", 0) / 1e9
                end_time = root_span.get("end_time", 0) / 1e9
                duration = end_time - start_time

                summaries.append(
                    {
                        "trace_id": trace_id,
                        "name": root_span.get("name", "Unknown"),
                        "start_time": datetime.fromtimestamp(start_time).isoformat(),
                        "duration": duration,
                        "span_count": len(spans),
                    }
                )

        # Sort by start time
        summaries.sort(key=lambda s: s["start_time"], reverse=True)
        return summaries


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for the trace dashboard."""

    def __init__(self, *args, trace_data: TraceData, **kwargs):
        self.trace_data = trace_data
        super().__init__(*args, **kwargs)

    def do_GET(self):  # noqa: N802
        """Handle GET requests."""
        if self.path == "/":
            self.send_dashboard_html()
        elif self.path == "/api/traces":
            self.send_trace_summary()
        elif self.path.startswith("/api/trace/"):
            trace_id = self.path.split("/")[-1]
            self.send_trace_details(trace_id)
        else:
            self.send_error(404)

    def send_dashboard_html(self):
        """Send the dashboard HTML page."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dhenara Trace Viewer</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                h1 { color: #333; }
                table { width: 100%; border-collapse: collapse; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                tr:hover { background-color: #f5f5f5; }
                .trace-row { cursor: pointer; }
                .modal { display: none; position: fixed; z-index: 1; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4); }
                .modal-content { background-color: #fefefe; margin: 5% auto; padding: 20px; border: 1px solid #888; width: 90%; }
                .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
                .tree-view { font-family: monospace; }
                .tree-item { margin-left: 20px; }
                .tree-label { cursor: pointer; }
                .tree-content { display: none; }
            </style>
        </head>
        <body>
            <h1>Dhenara Trace Viewer</h1>
            <table id="trace-table">
                <thead>
                    <tr>
                        <th>Trace Name</th>
                        <th>Start Time</th>
                        <th>Duration (s)</th>
                        <th>Span Count</th>
                    </tr>
                </thead>
                <tbody id="trace-list"></tbody>
            </table>

            <div id="trace-modal" class="modal">
                <div class="modal-content">
                    <span class="close">&times;</span>
                    <h2 id="modal-title">Trace Details</h2>
                    <div id="trace-details" class="tree-view"></div>
                </div>
            </div>

            <script>
                // Fetch trace summary
                fetch('/api/traces')
                    .then(response => response.json())
                    .then(data => {
                        const traceList = document.getElementById('trace-list');
                        data.forEach(trace => {
                            const row = document.createElement('tr');
                            row.className = 'trace-row';
                            row.onclick = () => showTraceDetails(trace.trace_id);

                            row.innerHTML = `
                                <td>${trace.name}</td>
                                <td>${new Date(trace.start_time).toLocaleString()}</td>
                                <td>${trace.duration.toFixed(3)}</td>
                                <td>${trace.span_count}</td>
                            `;

                            traceList.appendChild(row);
                        });
                    });

                // Show trace details in modal
                function showTraceDetails(traceId) {
                    const modal = document.getElementById('trace-modal');
                    const modalTitle = document.getElementById('modal-title');
                    const traceDetails = document.getElementById('trace-details');

                    fetch(`/api/trace/${traceId}`)
                        .then(response => response.json())
                        .then(data => {
                            modalTitle.textContent = `Trace: ${data.name}`;

                            // Build tree view
                            traceDetails.innerHTML = '';
                            buildTreeView(traceDetails, data);

                            modal.style.display = 'block';
                        });
                }

                // Build a tree view for a trace
                function buildTreeView(container, node, depth = 0) {
                    const item = document.createElement('div');
                    item.className = 'tree-item';

                    const label = document.createElement('div');
                    label.className = 'tree-label';
                    label.textContent = `${node.name} (${node.duration.toFixed(3)}ms)`;

                    const content = document.createElement('div');
                    content.className = 'tree-content';

                    // Add attributes if any
                    if (node.attributes && Object.keys(node.attributes).length > 0) {
                        const attrDiv = document.createElement('div');
                        attrDiv.className = 'attributes';

                        const attrTitle = document.createElement('strong');
                        attrTitle.textContent = 'Attributes:';
                        attrDiv.appendChild(attrTitle);

                        const attrList = document.createElement('ul');
                        for (const [key, value] of Object.entries(node.attributes)) {
                            const attrItem = document.createElement('li');
                            attrItem.textContent = `${key}: ${value}`;
                            attrList.appendChild(attrItem);
                        }

                        attrDiv.appendChild(attrList);
                        content.appendChild(attrDiv);
                    }

                    // Add children if any
                    if (node.children && node.children.length > 0) {
                        node.children.forEach(child => {
                            buildTreeView(content, child, depth + 1);
                        });
                    }

                    // Toggle content visibility on label click
                    label.onclick = () => {
                        content.style.display = content.style.display === 'none' ? 'block' : 'none';
                    };

                    item.appendChild(label);
                    item.appendChild(content);
                    container.appendChild(item);
                }

                // Close the modal
                document.getElementsByClassName('close')[0].onclick = function() {
                    document.getElementById('trace-modal').style.display = 'none';
                }

                // Close modal if clicked outside
                window.onclick = function(event) {
                    const modal = document.getElementById('trace-modal');
                    if (event.target == modal) {
                        modal.style.display = 'none';
                    }
                }
            </script>
        </body>
        </html>
        """  # noqa: E501

        self.wfile.write(html.encode())

    def send_trace_summary(self):
        """Send trace summary as JSON."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        summary = self.trace_data.get_trace_summary()
        self.wfile.write(json.dumps(summary).encode())

    def send_trace_details(self, trace_id: str):
        """Send details for a specific trace as JSON."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        spans = self.trace_data.get_spans_for_trace(trace_id)

        if not spans:
            self.wfile.write(json.dumps({"error": "Trace not found"}).encode())
            return

        # Convert to hierarchical structure
        hierarchy = self._build_trace_hierarchy(spans)

        self.wfile.write(json.dumps(hierarchy).encode())

    def _build_trace_hierarchy(self, spans: list[dict[str, Any]]) -> dict[str, Any]:
        """Build a hierarchical structure from flat spans."""
        # Create a map of span_id to span
        span_map = {}
        for span in spans:
            if "span_id" in span:
                span_map[span["span_id"]] = span
            # If span has context with span_id, use that instead
            elif "context" in span and "span_id" in span["context"]:
                span_map[span["context"]["span_id"]] = span
                # Ensure span has a direct span_id for easier reference
                span["span_id"] = span["context"]["span_id"]

        # Find the root span (with no parent_id)
        root_spans = [s for s in spans if s.get("parent_id") is None]
        if not root_spans:
            return {"error": "No root span found"}

        root_span = root_spans[0]

        # Build hierarchy recursively
        return self._build_span_node(root_span, span_map)

    def _build_span_node(self, span: dict[str, Any], span_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Build a hierarchical node for a span."""
        # Get span_id from context if it exists, otherwise use direct span_id
        span_id = span.get("span_id")
        if not span_id and "context" in span:
            span_id = span.get("context", {}).get("span_id")

        # Convert nanoseconds to seconds for timestamps
        start_time = span.get("start_time", 0) / 1e9
        end_time = span.get("end_time", 0) / 1e9
        duration_ms = (end_time - start_time) * 1000

        # Create the node
        node = {
            "span_id": span_id,
            "name": span.get("name", "Unknown"),
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "duration": duration_ms,
            "attributes": span.get("attributes", {}),
            "children": [],
        }

        # Find and add children
        for potential_child in span_map.values():
            child_parent_id = potential_child.get("parent_id")
            # Also check in context if it exists
            if not child_parent_id and "context" in potential_child:
                child_parent_id = potential_child.get("context", {}).get("parent_id")

            if child_parent_id == span_id:
                child_node = self._build_span_node(potential_child, span_map)
                node["children"].append(child_node)

        return node


def run_dashboard(trace_file: str, port: int = 8080):
    """Run the trace dashboard server."""
    trace_data = TraceData(trace_file)

    # Custom server factory
    def handler_factory(*args, **kwargs):
        return DashboardHandler(*args, trace_data=trace_data, **kwargs)

    with socketserver.TCPServer(("", port), handler_factory) as httpd:
        print(f"Serving trace dashboard at http://localhost:{port}")
        print("Press Ctrl+C to stop")

        # Open browser automatically
        webbrowser.open(f"http://localhost:{port}")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down server")
            httpd.shutdown()


def main():
    """Command-line interface for the trace dashboard."""
    parser = argparse.ArgumentParser(description="Dhenara Trace Viewer")
    parser.add_argument("file", help="Path to the trace JSON file")
    parser.add_argument("--port", type=int, default=8080, help="Port for the dashboard server (default: 8080)")

    args = parser.parse_args()

    try:
        run_dashboard(args.file, args.port)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
