

class CustomHandlerRegistry:
    """Registry for custom handlers that can be dynamically registered."""

    def __init__(self):
        self._custom_handlers = {}

    def register(self, handler_id: str, handler_function: callable) -> None:
        """Register a custom handler function."""
        self._custom_handlers[handler_id] = handler_function

    def get_handler(self, handler_id: str) -> callable:
        """Get a custom handler function by ID."""
        handler = self._custom_handlers.get(handler_id)
        if not handler:
            raise ValueError(f"No custom handler registered with ID: {handler_id}")
        return handler
