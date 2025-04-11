from dhenara.agent.dsl.base import NodeOutcome, NodeOutput
from dhenara.agent.dsl.components.flow import FlowExecutionResult
from dhenara.ai.types.shared.base import BaseModel


class BasicAgentNodeOutputData(BaseModel):
    flow_execution_result: FlowExecutionResult | None


class BasicAgentNodeOutput(NodeOutput[BasicAgentNodeOutputData]):
    pass


class BasicAgentNodeOutcome(NodeOutcome):
    pass
