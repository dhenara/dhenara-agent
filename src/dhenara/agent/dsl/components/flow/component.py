from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutor,
)
from dhenara.agent.dsl.components.flow import FlowBlock, FlowElement, FlowExecutionContext, FlowNode, FlowNodeDefinition


class Flow(ComponentDefinition[FlowElement, FlowNode, FlowNodeDefinition, FlowExecutionContext]):
    node_class = FlowNode


class FlowExecutor(ComponentExecutor[FlowElement, FlowBlock, FlowExecutionContext, Flow]):
    block_class = FlowBlock
    context_class = FlowExecutionContext
    logger_path: str = "dhenara.dad.flow"
