from typing import Literal

from dhenara.agent.dsl.base import (
    ExecutableBlock,
    ExecutableElement,
    ExecutableNode,
    ExecutableNodeDefinition,
    ExecutableReference,
    NodeExecutor,
)
from dhenara.agent.dsl.components.flow import FlowExecutionContext


class FlowElement(ExecutableElement):
    """Base class for all elements in a flow."""

    pass


class FlowNodeDefinition(ExecutableNodeDefinition[FlowExecutionContext]):
    component_type: Literal["flow", "agent"] = "flow"


class FlowNodeExecutor(NodeExecutor):
    component_type: Literal["flow", "agent"] = "flow"


class FlowNode(ExecutableNode[FlowElement, FlowNodeDefinition, FlowExecutionContext]):
    """A single execution node in the flow."""

    pass


class FlowBlock(ExecutableBlock[FlowElement, FlowExecutionContext]):
    pass


class FlowReference(ExecutableReference):
    """A reference to a value in the context."""

    pass
