import asyncio
import contextvars
import functools
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import Span

from .profile import TracingDataCategory

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
            TracingDataCategory.primary.value: {},
            TracingDataCategory.secondary.value: {},
            TracingDataCategory.tertiary.value: {},
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
        key: str,
        value: Any,
        category: TracingDataCategory | str = TracingDataCategory.primary,
    ) -> None:
        """
        Add an attribute to be recorded in the trace.

        Args:
            key: Attribute key
            value: Attribute value
            category: Importance category ('primary', 'secondary', 'tertiary')
        """
        # Convert to string representation
        if isinstance(category, TracingDataCategory):
            category_str = category.value
        else:
            category_str = str(category)

        # Validate against allowed values
        if category_str not in ["primary", "secondary", "tertiary"]:
            category_str = "tertiary"  # Default to tertiary if invalid category

        self.attributes[category_str][key] = value

    def apply_to_span(self, span: Span) -> None:
        """Apply all collected attributes to a span."""
        for category, attrs in self.attributes.items():
            if isinstance(attrs, dict):
                # Update the dict (input, output etc) set via TracingProfile
                for key, value in attrs.items():
                    span.set_attribute(f"{category}.{key}", value)

    @classmethod
    def get_current(cls) -> Optional["TraceCollector"]:
        """Get the current trace collector from context, if any."""
        return _current_collector.get()


# Helper functions for easy attribute adding
def add_trace_attribute(
    key: str,
    value: Any,
    category: TracingDataCategory = TracingDataCategory.primary,
) -> bool:
    """
    Add an attribute to the current trace collector.

    Args:
        key: Attribute key
        value: Attribute value
        category: Importance category ('primary', 'secondary', 'tertiary')

    Returns:
        True if attribute was added, False if no collector is active
    """
    collector = TraceCollector.get_current()
    if collector:
        collector.add_attribute(key, value, category)
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
