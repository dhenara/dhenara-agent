# dhenara/agent/flow/flow.py


from dhenara.agent.dsl.base import ComponentDefinition, ComponentExecutor
from dhenara.agent.dsl.flow import FlowBlock, FlowElement, FlowExecutionContext, FlowNode, FlowNodeDefinition


class Flow(ComponentDefinition[FlowElement, FlowNode, FlowNodeDefinition, FlowExecutionContext]):
    node_class = FlowNode


class FlowExecutor(ComponentExecutor[FlowElement, FlowBlock, FlowExecutionContext, Flow]):
    pass
