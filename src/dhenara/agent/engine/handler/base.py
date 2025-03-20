from abc import ABC, abstractmethod
from typing import Any

from dhenara.agent.dsl.base import ExecutableNodeDefinition, ExecutionContext
from dhenara.agent.types import (
    NodeInput,
)
from dhenara.ai.types.resource import ResourceConfig


class NodeHandler(ABC):
    """Base handler for executing flow nodes.

    All node type handlers should inherit from this class and implement
    the handle method to process their specific node type.
    """

    def __init__(
        self,
        identifier: str,
    ):
        self.identifier = identifier

    @abstractmethod
    async def handle(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        resource_config: ResourceConfig,
    ) -> Any:
        """
        Handle the execution of a flow node.
        """
        pass

    def set_node_execution_failed(
        self,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        message: str,
    ):
        execution_context.execution_failed = True
        execution_context.execution_failed_message = message
