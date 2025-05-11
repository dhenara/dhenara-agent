from dhenara.agent.run import RunContext
from dhenara.agent.runner import AgentRunner

# Select the agent to run, and import its definitions
from src.agents.my_agent.agent import agent
from src.agents.my_agent.handler import node_input_event_handler
from src.runners.defs import observability_settings, project_root
from dhenara.agent.dsl.events import EventType
from dhenara.agent.utils.helpers.terminal import print_node_completion

# Select an agent to run, assignt it a root_id
root_component_id = "my_agent_root"
agent.root_id = root_component_id

# Create run context
run_context = RunContext(
    root_component_id=root_component_id,
    observability_settings=observability_settings,
    project_root=project_root,
)

# Register the event handlers
run_context.register_event_handlers(
    handlers_map={
        EventType.node_input_required: node_input_event_handler,
        EventType.node_execution_completed: print_node_completion,  # Optional
    }
)

# Create a runner
runner = AgentRunner(agent, run_context)

# Use dhenara cli to run this as in an isolated context
#  --  dhenara run agent <agent_name>
