import functools
import inspect
import time

from opentelemetry import baggage, trace
from opentelemetry.trace import Status, StatusCode

from dhenara.agent.observability.tracing import get_tracer, is_tracing_disabled
from dhenara.agent.observability.tracing.data import (
    ComponentTracingProfile,
    NodeTracingProfile,
    TraceCollector,
    span_attribute_manager,
)
from dhenara.agent.observability.tracing.tracing_log_handler import TraceLogCapture, inject_logs_into_span


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
            # If tracing is disabled, just call the original function
            if is_tracing_disabled():
                return await func(*args, **kwargs)

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
            hierarchy_path = None

            # Set baggage values if execution context available
            if execution_context:
                component_id = getattr(execution_context, "component_id", None)
                context_id = getattr(execution_context, "context_id", None)
                hierarchy_path = getattr(execution_context, "hierarchy_path", None)

                if component_id:
                    baggage.set_baggage("component.id", str(component_id))
                if node_id:
                    baggage.set_baggage("node.id", str(node_id))
                if context_id:
                    baggage.set_baggage("context.id", str(context_id))
                if hierarchy_path:
                    baggage.set_baggage("context.hierarchy_path", str(hierarchy_path))

            span_name = f"node.{detected_node_type}.execute"
            if hierarchy_path:
                span_name += f" - {hierarchy_path}"

            # Create the span with basic attributes
            with tracer.start_as_current_span(
                span_name,
                attributes={
                    "node.id": str(node_id),
                    "node.type": detected_node_type,
                    "node.hierarchy": hierarchy_path or "",
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
                        span_attribute_manager.add_profile_attributes(
                            span, execution_context, tracing_profile.context_fields
                        )

                    # Add input data based on profile
                    if node_input and tracing_profile.input_fields:
                        span_attribute_manager.add_profile_attributes(span, node_input, tracing_profile.input_fields)

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
                            span_attribute_manager.add_profile_attributes(span, result, tracing_profile.result_fields)

                        # Add output data based on profile
                        if result and hasattr(result, "output") and tracing_profile.output_fields:
                            span_attribute_manager.add_profile_attributes(
                                span, result.output, tracing_profile.output_fields
                            )

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
            # If tracing is disabled, just call the original function
            if is_tracing_disabled():
                return await func(*args, **kwargs)

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
            hierarchy_path = None

            # Set baggage values if execution context available
            if execution_context:
                component_id = getattr(execution_context, "component_id", None)
                context_id = getattr(execution_context, "context_id", None)
                hierarchy_path = getattr(execution_context, "hierarchy_path", None)

                if component_id:
                    baggage.set_baggage("component.id", str(component_id))
                if context_id:
                    baggage.set_baggage("context.id", str(context_id))
                if hierarchy_path:
                    baggage.set_baggage("context.hierarchy_path", str(hierarchy_path))

            span_name = f"{detected_component_type}.execute"
            if hierarchy_path:
                span_name += f" - {hierarchy_path}"

            # Create the span with basic attributes
            with tracer.start_as_current_span(
                span_name,
                attributes={
                    "component.id": str(component_id),
                    "component.type": detected_component_type,
                    "component.hierarchy": hierarchy_path or "",
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
                        span_attribute_manager.add_profile_attributes(
                            span, execution_context, tracing_profile.context_fields
                        )

                    # Add input data based on profile
                    if component_input and tracing_profile.input_fields:
                        span_attribute_manager.add_profile_attributes(
                            span, component_input, tracing_profile.input_fields
                        )

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
                            span_attribute_manager.add_profile_attributes(span, result, tracing_profile.result_fields)

                        # Add output data based on profile
                        if result and hasattr(result, "output") and tracing_profile.output_fields:
                            span_attribute_manager.add_profile_attributes(
                                span, result.output, tracing_profile.output_fields
                            )

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
