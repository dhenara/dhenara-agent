from dhenara.agent.dsl.base import (
    ExecutableBlock,
    ExecutableElement,
    ExecutableNode,
    ExecutableNodeDefinition,
    ExecutableReference,
)
from dhenara.agent.dsl.flow import FlowExecutionContext


class FlowElement(ExecutableElement):
    """Base class for all elements in a flow."""

    pass


class FlowNodeDefinition(ExecutableNodeDefinition[FlowExecutionContext]):
    """Node Denition"""

    pass


class FlowNode(ExecutableNode[FlowElement, FlowNodeDefinition, FlowExecutionContext]):
    """A single execution node in the flow."""

    pass


class FlowBlock(ExecutableBlock[FlowElement, FlowExecutionContext]):
    pass


class FlowReference(ExecutableReference):
    """A reference to a value in the context."""

    pass
