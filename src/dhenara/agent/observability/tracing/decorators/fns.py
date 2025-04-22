# dhenara/agent/observability/tracing/decorators/fns.py
import functools
import inspect
import time
from typing import Any

from opentelemetry import baggage, trace
from opentelemetry.trace import Span, Status, StatusCode

from dhenara.agent.observability.tracing import get_tracer
from dhenara.agent.observability.tracing.data import (
    ComponentTracingProfile,
    NodeTracingProfile,
    TraceCollector,
    TracingDataCategory,
    TracingDataField,
)
from dhenara.agent.observability.tracing.tracing_log_handler import TraceLogCapture, inject_logs_into_span

# Maximum string length for trace attributes
MAX_STRING_LENGTH = 4096
DEFAULT_PREVIEW_LENGTH = 500


def extract_value(obj: Any, path: str) -> Any:
    """Extract a value from an object using dot notation path."""
    if not path or not obj:
        return None

    parts = path.split(".")
    current = obj

    for part in parts:
        # Handle array/list indexing
        if "[" in part and part.endswith("]"):
            attr_name, idx_str = part.split("[", 1)
            idx = int(idx_str[:-1])  # Remove the closing bracket

            if attr_name:
                # Get the list/array first
                if hasattr(current, attr_name):
                    current = getattr(current, attr_name)
                elif isinstance(current, dict) and attr_name in current:
                    current = current[attr_name]
                else:
                    return None

            # Then access by index
            if isinstance(current, (list, tuple)) and 0 <= idx < len(current):
                current = current[idx]
            else:
                return None
        else:
            # Regular attribute or dict key
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

    return current


def truncate_string(value: str, max_length: int) -> str:
    """Truncate a string to max_length if needed."""
    if not isinstance(value, str):
        return value

    if len(value) <= max_length:
        return value

    return value[:max_length] + f"... [truncated, {len(value)} total]"


def sanitize_value(value: Any, max_length: int | None = None) -> Any:
    """Sanitize a value for use as a span attribute."""
    if value is None:
        return None

    if isinstance(value, (int, float, bool)):
        return value

    try:
        # Convert to string for other types
        str_value = str(value)

        # Apply truncation if requested
        if max_length and len(str_value) > max_length:
            return truncate_string(str_value, max_length)

        # Ensure we don't exceed OpenTelemetry's limits
        if len(str_value) > MAX_STRING_LENGTH:
            return truncate_string(str_value, MAX_STRING_LENGTH)

        return str_value
    except Exception:
        return "<unprintable>"


def add_profile_values_to_span(span: Span, data_object: Any, fields: list[TracingDataField], prefix: str = "") -> None:
    """Add values from a data object to a span based on tracing field definitions."""
    for field in fields:
        # Extract the value using the source path
        value = extract_value(data_object, field.source_path)

        # Skip if no value was found
        if value is None:
            continue

        # Apply transformation if specified
        if field.transform and callable(field.transform):
            try:
                value = field.transform(value)
            except Exception:
                # If transformation fails, use original value
                pass

        # Sanitize the value (truncate if needed)
        sanitized_value = sanitize_value(value, field.max_length)

        if isinstance(field.category, TracingDataCategory):
            category_str = field.category.value
        else:
            category_str = str(field.category)

        # Determine attribute name with category prefix
        attribute_name = f"{category_str}.{prefix}.{field.name}"

        # Add to span
        span.set_attribute(attribute_name, sanitized_value)


def trace_node(
    node_type: str | None = None,
    profile: NodeTracingProfile | None = None,
):
    """
    Decorator for tracing node execution.

    Args:
        node_type: Optional node type to use for profile lookup
                 (if None, will extract from node_definition)

    Returns:
        Decorated function with tracing
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract key parameters from function arguments
            bound_args = inspect.signature(func).bind(*args, **kwargs)
            bound_args.apply_defaults()
            all_args = bound_args.arguments

            # Extract common node parameters
            node_id = all_args.get("node_id", "unknown")
            node_definition = all_args.get("node_definition")
            execution_context = all_args.get("execution_context")
            node_input = all_args.get("node_input")

            # Get self if this is a method (for potential profile lookup)
            self = args[0] if args and hasattr(args[0], "__class__") else None

            # Determine node type - try multiple sources in order of preference
            detected_node_type = node_type
            if not detected_node_type and node_definition and hasattr(node_definition, "node_type"):
                detected_node_type = node_definition.node_type
            if not detected_node_type:
                detected_node_type = "unknown"

            # Get the profile to use - check multiple potential sources
            if profile:
                tracing_profile = profile
            else:
                if hasattr(self, "_tracing_profile"):
                    tracing_profile = self._tracing_profile
                else:
                    raise ValueError("No tracing profile found . The class should have a `_tracing_profile` member")

            # Create tracer and start timing
            tracer = get_tracer(f"dhenara.dad.node.{detected_node_type}")
            start_time = time.time()

            # Get tracing context for linking spans
            current_span = trace.get_current_span()
            parent_context = current_span.get_span_context() if current_span else None

            # Set baggage values if execution context available
            if execution_context:
                component_id = getattr(execution_context, "component_id", None)
                context_id = getattr(execution_context, "context_id", None)

                if component_id:
                    baggage.set_baggage("component.id", str(component_id))
                if context_id:
                    baggage.set_baggage("context.id", str(context_id))

            # Create the span with basic attributes
            with tracer.start_as_current_span(
                f"node.{detected_node_type}.execute",
                attributes={
                    "node.id": str(node_id),
                    "node.type": detected_node_type,
                    "execution.start_time": start_time,
                },
            ) as span:
                # Link to parent span if available
                if parent_context and parent_context.is_valid:
                    span.set_attribute("parent.trace_id", format(parent_context.trace_id, "032x"))
                    span.set_attribute("parent.span_id", format(parent_context.span_id, "016x"))

                # Start capturing logs for this span
                span_id = format(span.get_span_context().span_id, "016x")
                TraceLogCapture.start_capture(span_id)

                # Create a trace collector for this execution
                with TraceCollector(span=span) as _collector:
                    # Add execution context data
                    if execution_context:
                        # Add any fields from tracing profile
                        add_profile_values_to_span(span, execution_context, tracing_profile.context_fields, "context")

                        # Always include node hierarchy if available
                        if hasattr(execution_context, "hierarchy_path"):
                            hierarchy = execution_context.hierarchy_path
                            span.set_attribute("node.hierarchy", hierarchy)

                    # Add input data based on profile
                    if node_input and tracing_profile.input_fields:
                        add_profile_values_to_span(span, node_input, tracing_profile.input_fields, "input")

                    try:
                        # Execute the function
                        result = await func(*args, **kwargs)

                        # Calculate and record execution time
                        end_time = time.time()
                        duration_ms = (end_time - start_time) * 1000
                        span.set_attribute("execution.duration_ms", duration_ms)
                        span.set_attribute("execution.end_time", end_time)

                        # Add result data based on profile
                        if result and tracing_profile.result_fields:
                            add_profile_values_to_span(span, result, tracing_profile.result_fields, "result")

                        # Add output data based on profile
                        if result and hasattr(result, "output") and tracing_profile.output_fields:
                            add_profile_values_to_span(span, result.output, tracing_profile.output_fields, "output")

                        status_code = Status(StatusCode.ERROR)
                        success_status = "error"

                        if result and hasattr(result, "error"):
                            error_description = result.error
                        else:
                            error_description = "No Error Info available"

                        if result and hasattr(result, "execution_status"):
                            if result.execution_status in ["completed"]:  # ExecutionStatusEnum.COMPLETED
                                status_code = Status(StatusCode.OK)
                                success_status = "success"
                                error_description = None

                        span.set_status(status_code, error_description)
                        span.set_attribute("execution.status", success_status)

                        # Inject captured logs into the span
                        inject_logs_into_span(span)

                        return result
                    except Exception as e:
                        # Record error details
                        end_time = time.time()
                        duration_ms = (end_time - start_time) * 1000
                        span.set_attribute("execution.duration_ms", duration_ms)
                        span.set_attribute("execution.end_time", end_time)

                        # Record the error
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.set_attribute("execution.status", "error")
                        span.set_attribute("error.type", e.__class__.__name__)
                        span.set_attribute("error.message", str(e))

                        # Inject captured logs into the span
                        inject_logs_into_span(span)

                        raise

        return wrapper

    return decorator


def trace_component(
    component_type: str | None = None,
    profile: ComponentTracingProfile | None = None,
):
    """
    Decorator for tracing component execution.

    Args:
        component_type: Optional component type to use for profile lookup
                 (if None, will extract from component_definition)

    Returns:
        Decorated function with tracing
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract key parameters from function arguments
            bound_args = inspect.signature(func).bind(*args, **kwargs)
            bound_args.apply_defaults()
            all_args = bound_args.arguments

            # Extract common component parameters
            component_id = all_args.get("component_id", "unknown")
            # component_definition = all_args.get("component_definition")
            execution_context = all_args.get("execution_context")
            component_input = all_args.get("component_input")

            # Get self if this is a method (for potential profile lookup)
            self = args[0] if args and hasattr(args[0], "__class__") else None

            # Determine component type - try multiple sources in order of preference
            detected_component_type = component_type
            if not detected_component_type and hasattr(self, "component_type"):
                detected_component_type = self.component_type
            if not detected_component_type:
                detected_component_type = "unknown"

            # Get the profile to use - check multiple potential sources
            if profile:
                tracing_profile = profile
            else:
                if hasattr(self, "_tracing_profile"):
                    tracing_profile = self._tracing_profile
                else:
                    raise ValueError("No tracing profile found . The class should have a `_tracing_profile` member")

            # Create tracer and start timing
            tracer = get_tracer(f"dhenara.dad.{detected_component_type}")
            start_time = time.time()

            # Get tracing context for linking spans
            current_span = trace.get_current_span()
            parent_context = current_span.get_span_context() if current_span else None

            # Set baggage values if execution context available
            if execution_context:
                component_id = getattr(execution_context, "component_id", None)
                context_id = getattr(execution_context, "context_id", None)

                if component_id:
                    baggage.set_baggage("component.id", str(component_id))
                if context_id:
                    baggage.set_baggage("context.id", str(context_id))

            # Create the span with basic attributes
            with tracer.start_as_current_span(
                # f"component.{detected_component_type}.execute",
                f"{detected_component_type}.execute",
                attributes={
                    "component.id": str(component_id),
                    "component.type": detected_component_type,
                    "execution.start_time": start_time,
                },
            ) as span:
                # Link to parent span if available
                if parent_context and parent_context.is_valid:
                    span.set_attribute("parent.trace_id", format(parent_context.trace_id, "032x"))
                    span.set_attribute("parent.span_id", format(parent_context.span_id, "016x"))

                # Start capturing logs for this span
                span_id = format(span.get_span_context().span_id, "016x")
                TraceLogCapture.start_capture(span_id)

                # Create a trace collector for this execution
                with TraceCollector(span=span) as _collector:
                    # Add execution context data
                    if execution_context:
                        # Add any fields from tracing profile
                        add_profile_values_to_span(span, execution_context, tracing_profile.context_fields, "context")

                        # Always include component hierarchy if available
                        if hasattr(execution_context, "hierarchy_path"):
                            hierarchy = execution_context.hierarchy_path
                            span.set_attribute("component.hierarchy", hierarchy)

                    # Add input data based on profile
                    if component_input and tracing_profile.input_fields:
                        add_profile_values_to_span(span, component_input, tracing_profile.input_fields, "input")

                    try:
                        # Execute the function
                        result = await func(*args, **kwargs)

                        # Calculate and record execution time
                        end_time = time.time()
                        duration_ms = (end_time - start_time) * 1000
                        span.set_attribute("execution.duration_ms", duration_ms)
                        span.set_attribute("execution.end_time", end_time)

                        # Add result data based on profile
                        if result and tracing_profile.result_fields:
                            add_profile_values_to_span(span, result, tracing_profile.result_fields, "result")

                        # Add output data based on profile
                        if result and hasattr(result, "output") and tracing_profile.output_fields:
                            add_profile_values_to_span(span, result.output, tracing_profile.output_fields, "output")

                        status_code = Status(StatusCode.ERROR)
                        success_status = "error"

                        if result and hasattr(result, "error"):
                            error_description = result.error
                        else:
                            error_description = "No Error Info available"

                        if result and hasattr(result, "execution_status"):
                            if result.execution_status in ["completed"]:  # ExecutionStatusEnum.COMPLETED
                                status_code = Status(StatusCode.OK)
                                success_status = "success"
                                error_description = None

                        span.set_status(status_code, error_description)
                        span.set_attribute("execution.status", success_status)

                        # Inject captured logs into the span
                        inject_logs_into_span(span)

                        return result
                    except Exception as e:
                        # Record error details
                        end_time = time.time()
                        duration_ms = (end_time - start_time) * 1000
                        span.set_attribute("execution.duration_ms", duration_ms)
                        span.set_attribute("execution.end_time", end_time)

                        # Record the error
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.set_attribute("execution.status", "error")
                        span.set_attribute("error.type", e.__class__.__name__)
                        span.set_attribute("error.message", str(e))

                        # Inject captured logs into the span
                        inject_logs_into_span(span)

                        raise

        return wrapper

    return decorator
