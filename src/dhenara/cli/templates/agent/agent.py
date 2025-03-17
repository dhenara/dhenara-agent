from dhenara.agent.agent import BaseAgent

from .agent_def import agent_def


class Agent(BaseAgent):
    """
    {{agent_name}}

    {{agent_description}}
    """

    pass


agent = Agent(
    agent_definition=agent_def,
)
