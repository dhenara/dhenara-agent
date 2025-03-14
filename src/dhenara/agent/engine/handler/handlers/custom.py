from typing import Any

from dhenara.agent.engine.handler import NodeHandler
from dhenara.agent.types.flow import FlowContext, FlowNode
from dhenara.ai.types.resource import ResourceConfig


class CustomHandler(NodeHandler):
    def __init__(
        self,
        identifier: str,
    ):
        super().__init__(identifier=identifier)

    async def handle(self, flow_node: FlowNode, context: FlowContext, resource_config: ResourceConfig) -> Any:
        # Get the custom handler function registered for this node
        _handler_id = flow_node.custom_handler_id
        # handler_fn = custom_handler_registry.get_handler(handler_id)
        # return await handler_fn(flow_node, context)
