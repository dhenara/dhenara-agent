from dhenara.agent.dsl.events import EventType
from dhenara.agent.run import RunContext
from dhenara.agent.runner import AgentRunner
from dhenara.agent.utils.helpers.terminal import (
    print_component_completion,
    print_node_completion,
)

# Select the agent to run, and import its definitions
from src.agents.my_agent.agent import agent
from src.agents.my_agent.handler import node_input_event_handler
from src.runners.defs import project_root

# Select an agent to run, assign it a root_id
root_component_id = "my_agent_root"
agent.root_id = root_component_id

# Create run context
run_context = RunContext(
    root_component_id=root_component_id,
    project_root=project_root,
    observability_settings=None,  # pass observability_settings to enable tracing
    run_root_subpath=None,  # "agent_my_agent" Useful to pass when you have multiple agents in the same projects.
)


# Register the event handlers
run_context.register_event_handlers(
    handlers_map={
        EventType.node_input_required: node_input_event_handler,
        # Optional Notification events
        EventType.node_execution_completed: print_node_completion,
        EventType.component_execution_completed: print_component_completion,
    }
)

# Create a runner
runner = AgentRunner(agent, run_context)

# Use dhenara cli to run this as in an isolated context
#  --  dad agent run <agent_name>
