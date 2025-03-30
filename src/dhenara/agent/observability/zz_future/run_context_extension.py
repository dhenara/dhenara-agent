import logging

# from dhenara.agent.run import RunContext # TODO
from ..config import configure_observability


def initialize_observability(
    run_context,  # : RunContext,
    service_name: str | None = None,
    exporter_type: str = "console",
    otlp_endpoint: str | None = None,
) -> None:
    """Initialize observability for a run context.

    Args:
        run_context: The run context to instrument
        service_name: Service name for observability (defaults to agent_identifier)
        exporter_type: Exporter type ('console', 'otlp')
        otlp_endpoint: OTLP endpoint URL
    """
    # Use agent_identifier as service name if not provided
    if not service_name:
        service_name = f"dhenara-agent-{run_context.agent_identifier}"

    # Configure observability
    configure_observability(
        service_name=service_name,
        exporter_type=exporter_type,
        otlp_endpoint=otlp_endpoint,
        logging_level=logging.INFO,
    )

    # Instrument the event bus to capture event-related spans
    original_publish = run_context.event_bus.publish

    async def instrumented_publish(event):
        # Get tracer
        from ..tracing import get_tracer

        tracer = get_tracer("dhenara.agent.events")

        # Create span
        with tracer.start_as_current_span(
            f"event.{event.type}",
            attributes={
                "event.type": event.type,
                "event.nature": event.nature,
            },
        ) as span:
            try:
                # Execute original publish
                result = await original_publish(event)

                # Add result info to span
                if hasattr(event, "handled"):
                    span.set_attribute("event.handled", event.handled)

                return result
            except Exception as e:
                # Record error in span
                span.record_exception(e)
                span.set_attribute("error", str(e))
                raise

    # Replace the event bus publish method
    run_context.event_bus.publish = instrumented_publish
