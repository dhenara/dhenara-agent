from dhenara.agent.dsl.base import NodeOutcome, NodeOutput
from dhenara.ai.types.shared.base import BaseModel


class BasicAgentNodeOutputData(BaseModel):
    status_str: str = ""  # TODO


class BasicAgentNodeOutput(NodeOutput[BasicAgentNodeOutputData]):
    pass


class BasicAgentNodeOutcome(NodeOutcome):
    pass
