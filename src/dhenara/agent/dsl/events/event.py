from abc import ABC
from datetime import datetime

from dhenara.agent.types.base import BaseEnum


class EventNature(BaseEnum):
    # Simple Non blocking event for data exchange
    notify = "notify"
    # Event Modification Pattern - The event object itself is modified by handlers
    with_wait = "with_wait"
    # Callback/Future Pattern - The requester provides a way to receive the response asynchronously
    with_future = "with_future"  # Not supported now


class EventType(BaseEnum):
    node_input_required = "node_input_required"
    node_execution_start = "node_execution_start"
    node_execution_complete = "node_execution_complete"
    flow_execution_start = "flow_execution_start"
    flow_execution_complete = "flow_execution_complete"
    custom = "custom"


class BaseEvent(ABC):
    type: EventType
    nature: EventNature

    def __init__(self):
        self.handled = False  # Flag to indicate if any handler processed it
        self.timestamp = datetime.now()


class NodeInputRequiredEvent(BaseEvent):
    type = EventType.node_input_required
    nature = EventNature.with_wait

    def __init__(self, node_id, node_type):
        super().__init__()
        self.node_id = node_id
        self.node_type = node_type
        self.node_input = None  # Field to be filled by handlers

    def as_dict(self):
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "node_input": self.node_input,
        }


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
