from dhenara.agent.agent import BaseAgent

from .agent_def import agent_def
from .inputs.initial import initial_input


class Agent(BaseAgent):
    """
    {{agent_name}}

    {{agent_description}}
    """

    pass


agent = Agent(
    agent_definition=agent_def,
    initial_input=initial_input,
)
