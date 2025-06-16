import logging
from collections import defaultdict
from collections.abc import Callable

from dhenara.agent.observability.logging import log_with_context

from .event import BaseEvent, EventNature, EventType

logger = logging.getLogger(__name__)


class EventBus:
    """Simple event bus for node communication"""

    def __init__(self):
        self._handlers = defaultdict(list)  # subscribers

    def register(self, event_type: EventType, handler: Callable):
        """Register a handler for an event type."""
        self._handlers[event_type].append(handler)

    def register_wildcard(self, handler: Callable):
        """Register a handler for all event types."""
        self._handlers["*"].append(handler)

    async def publish(self, event: BaseEvent):
        """Publish an event to all registered handlers."""
        event_type = event.type
        handlers = self._handlers.get(event_type, [])
        # Get wildcard subscribers
        handlers += self._handlers.get("*", [])

        try:
            for handler in handlers:
                if event.nature == EventNature.notify:
                    await handler(event)  # TODO: Review  and make sure the handler is not blocking execution
                elif event.nature == EventNature.with_wait:
                    await handler(event)
                elif event.nature == EventNature.with_future:
                    await handler(event)  # TODO: Review  and make sure the handler is not blocking execution
                else:
                    raise ValueError(f"Unknown event nature {event.nature}")
        except Exception as e:
            # Log the error but don't stop event propagation
            log_with_context(logger, logging.INFO, f"Error handling event {event.type}: {e}")

        return event

    # TODO_FUTURE
    # def get_events(self, event_type: str | None = None):
    #    """Get all events, optionally filtered by type"""
    #    if event_type:
    #        return [e for e in self._events if e["type"] == event_type]
    #    return self._events
