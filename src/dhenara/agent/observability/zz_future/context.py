import time
import uuid
from typing import Any


# TODO_FUTURE
class ObservabilityContext:
    """
    Context for tracking observability data throughout agent execution.
    """

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or str(uuid.uuid4())
        self.trace_id = None
        self.start_time = time.time()
        self.end_time = None
        self.duration = None

        # Track node executions
        self.nodes: dict[str, dict[str, Any]] = {}

        # Track metrics
        self.metrics: dict[str, Any] = {}

        # Track errors
        self.errors: list[dict[str, Any]] = []

    def start_node(self, node_id: str) -> None:
        """Record the start of a node's execution."""
        self.nodes[node_id] = {"start_time": time.time(), "status": "running"}

    def end_node(self, node_id: str, status: str = "success", error=None) -> None:
        """Record the end of a node's execution."""
        if node_id in self.nodes:
            end_time = time.time()
            self.nodes[node_id].update(
                {"end_time": end_time, "duration": end_time - self.nodes[node_id]["start_time"], "status": status}
            )

            if error:
                self.nodes[node_id]["error"] = str(error)
                self.errors.append({"node_id": node_id, "error": str(error), "time": end_time})

    def record_metric(self, name: str, value: Any) -> None:
        """Record a metric."""
        self.metrics[name] = value

    def complete(self) -> None:
        """Mark the execution as complete."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """Convert the context to a dictionary."""
        return {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "nodes": self.nodes,
            "metrics": self.metrics,
            "errors": self.errors,
        }
