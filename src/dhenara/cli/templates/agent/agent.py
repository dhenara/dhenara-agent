from dhenara.agent.agent import BaseAgent

from .agent_def import agent_def
from .agent_def import agent_identifier as agent_id


class Agent(BaseAgent):
    """
    {{agent_name}}

    {{agent_description}}
    """

    pass


agent_identifier = agent_id

agent = Agent(
    agent_definition=agent_def,
)
