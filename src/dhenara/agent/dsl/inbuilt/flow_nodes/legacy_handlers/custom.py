from typing import Any

from dhenara.agent.dsl.base import ExecutableNodeDefinition, ExecutionContext
from dhenara.agent.engine.handler import NodeHandler
from dhenara.agent.types.flow import NodeInput
from dhenara.ai.types.resource import ResourceConfig


class CustomHandler(NodeHandler):
    def __init__(
        self,
        identifier: str,
    ):
        super().__init__(identifier=identifier)

    async def handle(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        resource_config: ResourceConfig,
    ) -> Any:
        # Get the custom handler function registered for this node
        _handler_id = node_definition.custom_handler_id
        # handler_fn = custom_handler_registry.get_handler(handler_id)
        # return await handler_fn(node_definition, context)
