import asyncio
import contextvars
import functools
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import Span

from .attribute_manager import span_attribute_manager
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
        self.attributes: list[tuple[TracingAttribute, Any]] = []  # Simple list of (attribute, value) tuples
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
            attribute: TracingAttribute instance
            value: Attribute value
        """
        # Validate attribute type
        if not isinstance(attribute, TracingAttribute):
            raise ValueError(
                f"attribute should be an instance of TracingAttribute, not {type(attribute)}. attribute={attribute}"
            )

        self.attributes.append((attribute, value))

    def apply_to_span(self, span: Span) -> None:
        """Apply all collected attributes to a span."""
        for attribute, value in self.attributes:
            # Use the SpanAttributeManager for consistent processing
            span_attribute_manager.add_attribute(
                span=span,
                attribute=attribute,
                value=value,
                prefix=None,
            )

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
        attribute: TracingAttribute instance
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
            attr = TracingAttribute(name='my_key', category='primary')
            add_trace_attribute(attr, 'my_value')
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
