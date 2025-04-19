from dhenara.agent.dsl import AgentDefinition

from .flow import flow

# Main Agent Definition
agent = AgentDefinition()

agent.flow(
    "agent_1",
    flow,
)
