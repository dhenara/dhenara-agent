from dhenara.agent.dsl import AgentDefinition

from .flow import chatbot_flow

# Main Agent Definition
agent = AgentDefinition()
agent.flow(
    "chatbot_flow",
    chatbot_flow,
)
