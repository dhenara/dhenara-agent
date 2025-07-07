import asyncio
import functools
import inspect
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

from dhenara.agent.observability.tracing import get_tracer, is_tracing_disabled
from dhenara.agent.observability.tracing.data import TracingAttribute, span_attribute_manager
from dhenara.agent.observability.tracing.data.attribute_defs.fn_attributes import (
    fn_class_attr,
    fn_code_namespace_attr,
    fn_error_message_attr,
    fn_error_type_attr,
    fn_execution_time_attr,
    fn_method_attr,
    fn_result_keys_attr,
    fn_result_size_attr,
    fn_result_status_attr,
    fn_result_status_code_attr,
    fn_result_success_attr,
    fn_result_type_attr,
)
from dhenara.agent.observability.tracing.data.attribute_defs.generic_attributes import (
    parent_span_id_attr,
    parent_trace_id_attr,
)

# Type variable for functions
F = TypeVar("F", bound=Callable[..., Any])


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

            # Create tracer
            tracer = get_tracer(f"dhenara.dad.{class_name.lower()}")

            # Start a span
            with tracer.start_as_current_span(f"{class_name}.{span_name}") as span:
                # Add basic method attributes using span_attribute_manager
                span_attribute_manager.add_attribute(span, fn_class_attr, class_name)
                span_attribute_manager.add_attribute(span, fn_method_attr, func.__name__)
                span_attribute_manager.add_attribute(span, fn_code_namespace_attr, func.__module__)

                # Add parent relationship if available
                if current_span_context.is_valid:
                    span_attribute_manager.add_attribute(
                        span, parent_trace_id_attr, format(current_span_context.trace_id, "032x")
                    )
                    span_attribute_manager.add_attribute(
                        span, parent_span_id_attr, format(current_span_context.span_id, "016x")
                    )

                # Add selected arguments as attributes
                if capture_args:
                    for arg_name in capture_args:
                        if arg_name in all_args and arg_name != "self":
                            # Create a dynamic TracingAttribute for the argument
                            arg_attr = TracingAttribute(
                                name=f"fn_arg.{arg_name}",
                                category="secondary",
                                group_name="fn_trace",
                                data_type="string",
                                display_name=arg_name.replace("_", " ").title(),
                                description=f"Function argument: {arg_name}",
                                max_length=500,
                            )
                            span_attribute_manager.add_attribute(span, arg_attr, all_args[arg_name])

                try:
                    # Execute the function
                    result = await func(self, *args, **kwargs)

                    # Record execution time
                    execution_time = time.time() - start_time
                    span_attribute_manager.add_attribute(span, fn_execution_time_attr, execution_time * 1000)

                    # Add result metadata if requested
                    if capture_result:
                        _add_result_attributes(span, result)

                    # Set success status
                    span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Record execution time even for errors
                    execution_time = time.time() - start_time
                    span_attribute_manager.add_attribute(span, fn_execution_time_attr, execution_time * 1000)

                    # Record the error
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span_attribute_manager.add_attribute(span, fn_error_type_attr, e.__class__.__name__)
                    span_attribute_manager.add_attribute(span, fn_error_message_attr, str(e))
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

            # Create tracer
            tracer = get_tracer(f"dhenara.dad.{class_name.lower()}")

            # Start a span
            with tracer.start_as_current_span(f"{class_name}.{span_name}") as span:
                # Add basic method attributes using span_attribute_manager
                span_attribute_manager.add_attribute(span, fn_class_attr, class_name)
                span_attribute_manager.add_attribute(span, fn_method_attr, func.__name__)
                span_attribute_manager.add_attribute(span, fn_code_namespace_attr, func.__module__)

                # Add parent relationship if available
                if current_span_context.is_valid:
                    span_attribute_manager.add_attribute(
                        span, parent_trace_id_attr, format(current_span_context.trace_id, "032x"), "parent"
                    )
                    span_attribute_manager.add_attribute(
                        span, parent_span_id_attr, format(current_span_context.span_id, "016x"), "parent"
                    )

                # Add selected arguments as attributes
                if capture_args:
                    for arg_name in capture_args:
                        if arg_name in all_args and arg_name != "self":
                            # Create a dynamic TracingAttribute for the argument
                            arg_attr = TracingAttribute(
                                name=f"fn_arg.{arg_name}",
                                category="secondary",
                                group_name="fn_trace",
                                data_type="string",
                                display_name=arg_name.replace("_", " ").title(),
                                description=f"Function argument: {arg_name}",
                                max_length=500,
                            )
                            span_attribute_manager.add_attribute(span, arg_attr, all_args[arg_name])

                try:
                    # Execute the function
                    result = func(self, *args, **kwargs)

                    # Record execution time
                    execution_time = time.time() - start_time
                    span_attribute_manager.add_attribute(span, fn_execution_time_attr, execution_time * 1000)

                    # Add result metadata if requested
                    if capture_result:
                        _add_result_attributes(span, result)

                    # Set success status
                    span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Record execution time even for errors
                    execution_time = time.time() - start_time
                    span_attribute_manager.add_attribute(span, fn_execution_time_attr, execution_time * 1000)

                    # Record the error
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span_attribute_manager.add_attribute(span, fn_error_type_attr, e.__class__.__name__)
                    span_attribute_manager.add_attribute(span, fn_error_message_attr, str(e))
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


def _add_result_attributes(span: Span, result: Any) -> None:
    """Add metadata about a function result to a span.

    Args:
        span: The span to add attributes to
        result: The result to add metadata for
    """
    if result is None:
        span_attribute_manager.add_attribute(span, fn_result_type_attr, "None")
        return

    # Add result type
    span_attribute_manager.add_attribute(span, fn_result_type_attr, type(result).__name__)

    # For collections, add size
    if hasattr(result, "__len__"):
        try:
            span_attribute_manager.add_attribute(span, fn_result_size_attr, len(result))
        except (TypeError, AttributeError):
            pass

    # For dictionaries, add keys (limited)
    if isinstance(result, dict):
        try:
            keys = list(result.keys())
            if keys:
                span_attribute_manager.add_attribute(span, fn_result_keys_attr, keys[:5])
        except Exception:
            pass

    # For common result types with status
    if hasattr(result, "status"):
        span_attribute_manager.add_attribute(span, fn_result_status_attr, result.status)

    # For HTTP responses
    if hasattr(result, "status_code"):
        span_attribute_manager.add_attribute(span, fn_result_status_code_attr, result.status_code)

    # For many Dhenara response objects
    if hasattr(result, "was_successful"):
        span_attribute_manager.add_attribute(span, fn_result_success_attr, bool(result.was_successful))
