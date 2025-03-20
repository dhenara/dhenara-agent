from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from typing import Any


class EventBus:
    """Simple event bus for node communication"""

    def __init__(self):
        self._subscribers = defaultdict(list)
        self._events = []

    async def publish(self, event_type: str, data: Any, source_id: str):
        """Publish an event to all subscribers"""
        event = {"type": event_type, "data": data, "source_id": source_id, "timestamp": datetime.now()}
        self._events.append(event)

        # Notify subscribers
        for callback in self._subscribers.get(event_type, []):
            await callback(event)

        # Notify wildcard subscribers
        for callback in self._subscribers.get("*", []):
            await callback(event)

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to events of a specific type"""
        self._subscribers[event_type].append(callback)

    def get_events(self, event_type: str | None = None):
        """Get all events, optionally filtered by type"""
        if event_type:
            return [e for e in self._events if e["type"] == event_type]
        return self._events
