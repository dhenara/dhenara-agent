from dhenara.agent.agent import BaseAgent
from dhenara.agent.dsl import AgentNode

from ._sample_flows.chatbot_with_summarizer import flow

# Agent definition,  modify as per your need
# NOTE: The instance name should be `agent_definition`
agent_node = AgentNode(
    id="{{agent_identifier}}_node",
    independent=True,
    multi_phase=False,
    description="",
    flow=flow,
)


class MyAgent(BaseAgent):
    """
    {{agent_name}}
    {{agent_description}}
    """

    agent_id = "{{agent_identifier}}"
    agent_node = agent_node
