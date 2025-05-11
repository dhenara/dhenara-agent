from dhenara.agent.run import RunContext
from dhenara.agent.runner import AgentRunner

# Select the agent to run, and import its definitions
from src.agents.my_agent.agent import agent
from src.agents.my_agent.inputs.handler import event_handler
from src.runners.defs import observability_settings, project_root

# Select an agent to run, assignt it a root_id
root_component_id = "my_agent_root"
agent.root_id = root_component_id

# Create run context
run_context = RunContext(
    root_component_id=root_component_id,
    observability_settings=observability_settings,
    project_root=project_root,
)

# Register the input handlers
run_context.register_node_input_handler(event_handler)

# Create a runner
runner = AgentRunner(agent, run_context)

# Use dhenara cli to run this as in an isolated context
#  --  dhenara run agent <agent_name>
