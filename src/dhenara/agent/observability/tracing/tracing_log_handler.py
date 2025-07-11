import logging
import threading
from collections import defaultdict

from opentelemetry.trace import Span

from .data import add_trace_attribute
from .data.attribute_defs.generic_attributes import (
    trace_debugs_attr,
    trace_errors_attr,
    trace_infos_attr,
    trace_warnings_attr,
)

# INFO: These fns are used to add `log` data to traces naturally.
# The idea is to get max debug info from the traces in case of errors/warnings


class TraceLogCapture:
    """Thread-local storage for capturing logs during trace execution."""

    _thread_local = threading.local()

    @classmethod
    def start_capture(cls, span_id: str | None = None):
        """Start capturing logs for the current thread."""
        if not hasattr(cls._thread_local, "logs"):
            cls._thread_local.logs = defaultdict(list)
        if not hasattr(cls._thread_local, "active_spans"):
            cls._thread_local.active_spans = []

        if span_id:
            cls._thread_local.active_spans.append(span_id)

    @classmethod
    def stop_capture(cls, span_id: str | None = None):
        """Stop capturing logs and return the captured logs."""
        if span_id and hasattr(cls._thread_local, "active_spans"):
            if span_id in cls._thread_local.active_spans:
                cls._thread_local.active_spans.remove(span_id)

        if not hasattr(cls._thread_local, "logs"):
            return {}

        logs = dict(cls._thread_local.logs)
        cls._thread_local.logs.clear()
        return logs

    @classmethod
    def add_log(cls, record: logging.LogRecord):
        """Add a log record to the current capture."""
        if not hasattr(cls._thread_local, "logs") or not hasattr(cls._thread_local, "active_spans"):
            return

        if not cls._thread_local.active_spans:
            return

        # Format the log message
        log_entry = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": record.created,
        }

        # Add exception info if present
        if record.exc_info:
            _, exc_value, _ = record.exc_info
            log_entry["exception"] = str(exc_value)

        # Add to all active spans
        for span_id in cls._thread_local.active_spans:
            cls._thread_local.logs[span_id].append(log_entry)


class TraceLogHandler(logging.Handler):
    """Logging handler that captures logs and adds them to trace spans."""

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    def emit(self, record):
        """Emit a log record to the current trace capture."""
        TraceLogCapture.add_log(record)


def inject_logs_into_span(span: Span):
    """Inject captured logs into a span as attributes."""
    from dhenara.agent.observability.config import get_current_settings

    # Get the threshold from settings
    level_threshold_str = get_current_settings().trace_log_level
    level_threshold = getattr(logging, level_threshold_str.upper())

    span_id = format(span.get_span_context().span_id, "016x")
    logs = TraceLogCapture.stop_capture(span_id)

    if not logs or span_id not in logs:
        return

    captured_logs = logs[span_id]

    # Group logs by level
    errors = []
    warnings = []
    infos = []
    debugs = []

    for log in captured_logs:
        level_num = logging._nameToLevel.get(log["level"], logging.NOTSET)
        if level_num < level_threshold:
            continue

        if log["level"] == "ERROR" or log["level"] == "CRITICAL" or "exception" in log:
            errors.append(log["message"] + (f": {log['exception']}" if "exception" in log else ""))
        elif log["level"] == "WARNING":
            warnings.append(log["message"])
        elif log["level"] == "INFO":
            infos.append(log["message"])
        elif log["level"] == "DEBUG":
            debugs.append(log["message"])

    # Add to span attributes
    if errors:
        add_trace_attribute(trace_errors_attr, errors)

    if warnings:
        add_trace_attribute(trace_warnings_attr, warnings)

    if infos:
        add_trace_attribute(trace_infos_attr, infos)

    if debugs:
        add_trace_attribute(trace_debugs_attr, debugs)
