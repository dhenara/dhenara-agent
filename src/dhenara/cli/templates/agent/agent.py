from dhenara.agent.agent import BaseAgent

# NOTE: Do not remove below 2 lines
from .agent_def import agent_definition
from .agent_def import agent_identifier as agent_id


class MyAgent(BaseAgent):
    """
    {{agent_name}}

    {{agent_description}}
    """

    pass


# NOTE:  Do not modifiy below line
agent_identifier = agent_id

# Create agent instance
# NOTE: The object name should be `agent`
agent = MyAgent(
    agent_definition=agent_definition,  # pass agent_definition
)
