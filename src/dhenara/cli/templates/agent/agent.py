from dhenara.agent.agent import BaseAgent

# NOTE: Do not remove below  lines
from .agent_def import agent_id, agent_node


class MyAgent(BaseAgent):
    """
    abcd


    """

    pass


# NOTE:  Do not modifiy below line
agent_identifier = agent_id

# Create agent instance
# NOTE: The object name should be `agent`
agent = MyAgent(
    agent_node=agent_node,  # pass agent_definition
)
