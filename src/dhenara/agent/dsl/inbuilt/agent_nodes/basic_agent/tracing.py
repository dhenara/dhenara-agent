from dhenara.agent.dsl.inbuilt.agent_nodes.defs import AgentNodeTypeEnum
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
)

# Define AI Model Node tracing profile
basic_agent_node_tracing_profile = NodeTracingProfile(
    node_type=AgentNodeTypeEnum.basic_agent.value,
    # Primary input data - what's being sent to the model
    input_fields=[],
    # Primary output data - what's coming back from the model
    output_fields=[],
    # Result data - processed outcomes and metadata
    result_fields=[],
)
