from dhenara.agent.dsl import Agent, BasicAgentNode

from .flow import flow

agent = Agent()
agent.node(
    "agent_1",
    BasicAgentNode(
        flow=flow,
        settings=None,
    ),
)
