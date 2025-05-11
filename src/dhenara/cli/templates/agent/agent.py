from dhenara.agent.dsl import AgentDefinition

from .flow import main_flow

agent = AgentDefinition()
agent.flow(
    "main_flow",
    main_flow,
)
