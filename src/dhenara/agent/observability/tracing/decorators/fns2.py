import asyncio
import functools
import inspect
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

from dhenara.agent.observability.tracing import get_tracer, is_tracing_disabled
from dhenara.agent.observability.tracing.decorators.fns import span_attribute_manager

# Default service name
DEFAULT_SERVICE_NAME = "dhenara-dad"


# Type variable for functions
F = TypeVar("F", bound=Callable[..., Any])


def add_result_attributes(span: Span, result: Any) -> None:
    """Add metadata about a function result to a span.

    Args:
        span: The span to add attributes to
        result: The result to add metadata for
    """
    if result is None:
        span.set_attribute("result.type", "None")
        return

    # Add result type
    span.set_attribute("result.type", type(result).__name__)

    # For collections, add size
    if hasattr(result, "__len__"):
        try:
            span.set_attribute("result.size", len(result))
        except (TypeError, AttributeError):
            pass

    # For dictionaries, add keys (limited)
    if isinstance(result, dict):
        try:
            keys = list(result.keys())
            if keys:
                # Use span_attribute_manager for consistent serialization
                serialized_keys = span_attribute_manager.serialize_value(keys[:5])
                span.set_attribute("result.keys", serialized_keys)
        except Exception:
            pass

    # For common result types with status
    if hasattr(result, "status"):
        serialized_status = span_attribute_manager.serialize_value(result.status)
        span.set_attribute("result.status", serialized_status)

    # For HTTP responses
    if hasattr(result, "status_code"):
        span.set_attribute("result.status_code", result.status_code)

    # For many Dhenara response objects
    if hasattr(result, "was_successful"):
        span.set_attribute("result.success", bool(result.was_successful))


def trace_method(
    name: str | None = None,
    capture_args: list[str] | None = None,
    capture_result: bool = True,
) -> Callable[[F], F]:
    """General purpose method decorator for tracing any method.

    Args:
        name: Optional custom name for the span
        capture_args: Optional list of argument names to capture as span attributes
        capture_result: Whether to capture metadata about the result

    Returns:
        Decorated method with tracing
    """

    def decorator(func: F) -> F:
        sig = inspect.signature(func)

        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # If tracing is disabled, just call the original function
            if is_tracing_disabled():
                return await func(self, *args, **kwargs)

            start_time = time.time()

            # Create span name from function name or provided name
            span_name = name if name else func.__name__

            # Get class name
            class_name = self.__class__.__name__

            # Bind args to signature for introspection
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            all_args = bound_args.arguments

            # Get current context for parent relationship
            current_span_context = trace.get_current_span().get_span_context()
            parent_attributes = {}
            if current_span_context.is_valid:
                parent_attributes["parent.trace_id"] = format(current_span_context.trace_id, "032x")
                parent_attributes["parent.span_id"] = format(current_span_context.span_id, "016x")

            # Create tracer
            tracer = get_tracer(f"dhenara.dad.{class_name.lower()}")

            # Start a span
            with tracer.start_as_current_span(
                f"{class_name}.{span_name}",
                attributes={
                    "class": class_name,
                    "method": func.__name__,
                    "code.namespace": func.__module__,
                    **parent_attributes,
                },
            ) as span:
                # Add selected arguments as attributes
                if capture_args:
                    for arg_name in capture_args:
                        if arg_name in all_args and arg_name != "self":
                            # Use span_attribute_manager for consistent serialization
                            serialized_value = span_attribute_manager.serialize_value(all_args[arg_name])
                            span.set_attribute(f"arg.{arg_name}", serialized_value)

                try:
                    # Execute the function
                    result = await func(self, *args, **kwargs)

                    # Record execution time
                    execution_time = time.time() - start_time
                    span.set_attribute("execution.time_ms", execution_time * 1000)

                    # Add result metadata if requested
                    if capture_result:
                        add_result_attributes(span, result)

                    # Set success status
                    span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Record execution time even for errors
                    execution_time = time.time() - start_time
                    span.set_attribute("execution.time_ms", execution_time * 1000)

                    # Record the error
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("error.type", e.__class__.__name__)

                    # Use span_attribute_manager for consistent error message serialization
                    serialized_error = span_attribute_manager.serialize_value(str(e))
                    span.set_attribute("error.message", serialized_error)
                    raise

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            # If tracing is disabled, just call the original function
            if is_tracing_disabled():
                return func(self, *args, **kwargs)

            start_time = time.time()

            # Create span name from function name or provided name
            span_name = name if name else func.__name__

            # Get class name
            class_name = self.__class__.__name__

            # Bind args to signature for introspection
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            all_args = bound_args.arguments

            # Get current context for parent relationship
            current_span_context = trace.get_current_span().get_span_context()
            parent_attributes = {}
            if current_span_context.is_valid:
                parent_attributes["parent.trace_id"] = format(current_span_context.trace_id, "032x")
                parent_attributes["parent.span_id"] = format(current_span_context.span_id, "016x")

            # Create tracer
            tracer = get_tracer(f"dhenara.dad.{class_name.lower()}")

            # Start a span
            with tracer.start_as_current_span(
                f"{class_name}.{span_name}",
                attributes={
                    "class": class_name,
                    "method": func.__name__,
                    "code.namespace": func.__module__,
                    **parent_attributes,
                },
            ) as span:
                # Add selected arguments as attributes
                if capture_args:
                    for arg_name in capture_args:
                        if arg_name in all_args and arg_name != "self":
                            # Use span_attribute_manager for consistent serialization
                            serialized_value = span_attribute_manager.serialize_value(all_args[arg_name])
                            span.set_attribute(f"arg.{arg_name}", serialized_value)

                try:
                    # Execute the function
                    result = func(self, *args, **kwargs)

                    # Record execution time
                    execution_time = time.time() - start_time
                    span.set_attribute("execution.time_ms", execution_time * 1000)

                    # Add result metadata if requested
                    if capture_result:
                        add_result_attributes(span, result)

                    # Set success status
                    span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Record execution time even for errors
                    execution_time = time.time() - start_time
                    span.set_attribute("execution.time_ms", execution_time * 1000)

                    # Record the error
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("error.type", e.__class__.__name__)

                    # Use span_attribute_manager for consistent error message serialization
                    serialized_error = span_attribute_manager.serialize_value(str(e))
                    span.set_attribute("error.message", serialized_error)
                    raise

        # Choose the appropriate wrapper based on whether the function is async or not
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    # Handle case where decorator is used without parentheses
    if callable(name):
        func, name = name, None
        return decorator(func)

    return decorator
