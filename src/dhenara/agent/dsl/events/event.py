import warnings
from datetime import datetime
from typing import Any, TypeVar

from pydantic import Field

from dhenara.agent.types.base import BaseEnum, BaseModelABC
from dhenara.ai.types.shared.base import ISODateTime


class EventNature(BaseEnum):
    # Simple Non blocking event for data exchange
    notify = "notify"
    # Event Modification Pattern - The event object itself is modified by handlers
    with_wait = "with_wait"
    # Callback/Future Pattern - The requester provides a way to receive the response asynchronously
    with_future = "with_future"  # Not supported now


class EventType(BaseEnum):
    node_input_required = "node_input_required"
    node_execution_started = "node_execution_started"
    node_execution_completed = "node_execution_completed"
    component_execution_completed = "component_execution_completed"
    flow_execution_start = "flow_execution_start"
    flow_execution_complete = "flow_execution_complete"
    custom = "custom"


class BaseEvent(BaseModelABC):
    type: EventType
    nature: EventNature
    handled: bool = Field(default=False, description="Flag to indicate if any handler processed it")
    timestamp: ISODateTime = Field(default_factory=datetime.now)


BaseEventT = TypeVar("BaseEventT", bound=BaseEvent)


class NodeInputRequiredEvent(BaseEvent):
    type: EventType = Field(default=EventType.node_input_required, frozen=True)
    nature: EventNature = Field(default=EventNature.with_wait, frozen=True)
    node_id: str
    node_type: str
    node_def_settings: Any | None = None  # TODO_FUTURE: Should be of type NodeSettings
    node_input: Any | None = Field(default=None, description="Field to be filled by handlers")
    fe_data: dict | None = None

    @property
    def input(self) -> Any | None:
        """
        Deprecated: Use 'node_input' instead of 'input'.
        This property is maintained for backward compatibility and will be removed in a future version.
        """
        warnings.warn(
            "The 'input' field is deprecated. Use 'node_input' instead. "
            "This field will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.node_input

    @input.setter
    def input(self, value: Any | None) -> None:
        """
        Deprecated: Use 'node_input' instead of 'input'.
        This setter is maintained for backward compatibility and will be removed in a future version.
        """
        warnings.warn(
            "The 'input' field is deprecated. Use 'node_input' instead. "
            "This field will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.node_input = value


class NodeExecutionCompletedEvent(BaseEvent):
    type: EventType = Field(default=EventType.node_execution_completed, frozen=True)
    nature: EventNature = Field(default=EventNature.notify, frozen=True)
    node_id: str
    node_type: str
    node_outcome: Any | None = None


class ComponentExecutionCompletedEvent(BaseEvent):
    type: EventType = Field(default=EventType.component_execution_completed, frozen=True)
    nature: EventNature = Field(default=EventNature.notify, frozen=True)
    component_id: str
    component_type: str
    component_outcome: Any | None = None


EVENT_TYPE_REGISTRY = {
    EventType.node_input_required: NodeInputRequiredEvent,
    EventType.node_execution_completed: NodeExecutionCompletedEvent,
    EventType.component_execution_completed: ComponentExecutionCompletedEvent,
}


def get_event_class_for_type(event_type: EventType) -> type[BaseEvent] | None:
    """Get the appropriate event class for a given event type.

    Args:
        event_type: The EventType message type

    Returns:
        The corresponding event class, or None if not found
    """
    return EVENT_TYPE_REGISTRY.get(event_type)


# TODO_FUTURE: Implement below
# NodeInputRequiredEvent: When a node needs input
# NodeExecutionStartEvent: Before a node executes
# NodeExecutionCompleteEvent: After a node completes execution
# FlowExecutionStartEvent: When a flow starts
# FlowExecutionCompleteEvent: When a flow completes


## Log all node executions
# async def execution_logger(event: NodeExecutionEvent):
#    logger.info(f"Executing node {event.node_id} of type {event.node_type}")
#
# event_bus.register(NodeExecutionEvent, execution_logger)

## Track progress for UI updates
# async def progress_tracker(event: NodeExecutionCompleteEvent):
#    total_nodes = get_total_nodes()
#    completed_nodes = get_completed_nodes()
#    progress = completed_nodes / total_nodes * 100
#    await update_progress_ui(progress)
#
# event_bus.register(NodeExecutionCompleteEvent, progress_tracker)
#
#
## Add custom behavior without modifying core code
# async def special_node_handler(event: NodeExecutionEvent):
#    if event.node_id == "security_check":
#        # Add special security validation
#        event.context.security_validated = True
#
# event_bus.register(NodeExecutionEvent, special_node_handler)
