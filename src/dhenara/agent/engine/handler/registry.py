from dhenara.agent.engine.handler import NodeHandler
from dhenara.agent.types.flow import FlowNodeTypeEnum


class NodeHandlerRegistry:
    """Registry for node handlers.

    Provides a central management system for registering and retrieving
    handlers for different node types.
    """

    def __init__(self):
        self._handlers: dict[FlowNodeTypeEnum, type[NodeHandler]] = {}

    def register(self, node_type: FlowNodeTypeEnum, handler_class: type[NodeHandler]) -> None:
        """
        Register a handler class for a specific node type.

        Args:
            node_type: The type of node this handler can process
            handler_class: The handler class to register
        """
        self._handlers[node_type] = handler_class

    def get_handler(self, node_type: FlowNodeTypeEnum) -> type[NodeHandler]:
        """
        Get the handler class for a specific node type.

        Args:
            node_type: The type of node to get a handler for

        Returns:
            The handler class

        Raises:
            ValueError: If no handler is registered for the given node type
        """
        handler_class = self._handlers.get(node_type)
        if not handler_class:
            raise ValueError(f"No handler registered for node type: {node_type}")
        return handler_class
