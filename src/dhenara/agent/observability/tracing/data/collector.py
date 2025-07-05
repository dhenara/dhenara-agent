import asyncio
import contextvars
import functools
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import Span

from .profile import TracingAttribute

# Context variable to hold the current trace collector
_current_collector = contextvars.ContextVar("trace_collector", default=None)


class TraceCollector:
    """
    Collects trace attributes from various points of execution
    and applies them to the current span.
    """

    def __init__(self, span: Span | None = None):
        self.span = span
        self.attributes = {
            "primary": {},
            "secondary": {},
            "tertiary": {},
        }
        self._token = None

    def __enter__(self):
        self._token = _current_collector.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            _current_collector.reset(self._token)

        # If we have a span, apply all collected attributes
        if self.span:
            self.apply_to_span(self.span)

    def add_attribute(
        self,
        attribute: TracingAttribute,
        value: Any,
    ) -> None:
        """
        Add an attribute to be recorded in the trace.

        Args:
            key: Attribute key
            value: Attribute value
        """
        # Handle TracingAttribute instance
        if not isinstance(attribute, TracingAttribute):
            raise ValueError(
                f"attributeshould be an instance of TracingAttribute, not {type(attribute)}. attribute={attribute}"
            )

        # Apply transformation if specified
        if attribute.transform and callable(attribute.transform):
            try:
                value = attribute.transform(value)
            except Exception:
                # If transformation fails, use original value
                pass

        # Apply max_length if specified
        if attribute.max_length and isinstance(value, str) and len(value) > attribute.max_length:
            value = value[: attribute.max_length] + "... [truncated]"

        self.attributes[attribute.category][attribute.name] = value

    def apply_to_span(self, span: Span) -> None:
        """Apply all collected attributes to a span."""
        for category, attrs in self.attributes.items():
            if isinstance(attrs, dict):
                for key, value in attrs.items():
                    # Handle different types of values
                    serialized_value = self._serialize_value(value)
                    span.set_attribute(f"{category}.{key}", serialized_value)

    def _serialize_value(self, value: Any) -> Any:
        """
        Serialize a value to make it compatible with OpenTelemetry spans.

        OpenTelemetry supports: str, bool, int, float, and sequences of these types.
        """
        # Handle None
        if value is None:
            return "None"

        # Handle basic types that OTel supports directly
        if isinstance(value, (str, bool, int, float)):
            return value

        # Handle lists and tuples - recursively serialize each item
        if isinstance(value, (list, tuple)):
            # Only serialize up to 10 items to avoid huge spans
            serialized = [self._serialize_value(item) for item in value[:10]]
            if len(value) > 10:
                serialized.append("... (truncated)")
            return serialized

        # Handle dictionaries - recursively serialize each value
        if isinstance(value, dict):
            # Return a simplified representation for nested dicts
            simplified = {}
            # Only include first 10 keys to avoid huge spans
            for i, (k, v) in enumerate(value.items()):
                if i >= 10:
                    simplified["..."] = "(truncated)"
                    break
                simplified[str(k)] = self._serialize_value(v)
            return str(simplified)  # Convert to string to ensure OTel compatibility

        # Handle Pydantic models (or any object with a dict method)
        if hasattr(value, "dict") and callable(value.dict):
            try:
                # Convert Pydantic model to dict and then serialize
                return self._serialize_value(value.dict())
            except Exception:
                # Fallback to string representation
                return str(value)

        if hasattr(value, "model_dump") and callable(value.model_dump):
            try:
                # Convert Pydantic model to dict and then serialize
                return self._serialize_value(value.model_dump())
            except Exception:
                # Fallback to string representation
                return str(value)

        # For any other types, use string representation
        return str(value)

    @classmethod
    def get_current(cls) -> Optional["TraceCollector"]:
        """Get the current trace collector from context, if any."""
        return _current_collector.get()


# Helper functions for easy attribute adding
def add_trace_attribute(
    attribute: TracingAttribute,
    value: Any,
) -> bool:
    """
    Add an attribute to the current trace collector.

    Args:
        attribute: Attribute key
        value: Attribute value

    Returns:
        True if attribute was added, False if no collector is active
    """
    collector = TraceCollector.get_current()
    if collector:
        collector.add_attribute(attribute, value)
        return True
    return False


def trace_collect(**kwargs):
    """
    Decorator that provides a trace collector to the decorated function.

    Example:
        @trace_collect()
        def my_function():
            add_trace_attribute('my_key', 'my_value')
    """

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kw):
            # Get current span
            current_span = trace.get_current_span()

            # Create collector and set as current
            with TraceCollector(span=current_span):
                return await func(*args, **kw)

        @functools.wraps(func)
        def sync_wrapper(*args, **kw):
            # Get current span
            current_span = trace.get_current_span()

            # Create collector and set as current
            with TraceCollector(span=current_span):
                return func(*args, **kw)

        # Use appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
