from typing import Any

from dhenara.agent.engine.handler import NodeHandler
from dhenara.agent.types.flow import FlowContext, FlowNode
from dhenara.ai.types.resource import ResourceConfig


class RAGQueryHandler(NodeHandler):
    def __init__(
        self,
    ):
        super().__init__(identifier="rag_query_handler")

    async def handle(self, flow_node: FlowNode, context: FlowContext, resource_config: ResourceConfig) -> Any:
        # Implement RAG query logic
        pass
