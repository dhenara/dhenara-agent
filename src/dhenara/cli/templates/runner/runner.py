from dhenara.agent.run import RunContext
from dhenara.agent.runner import AgentRunner

# Select the agent to run, and import its definitions
from src.agents.chatbot.agent import agent
from src.agents.chatbot.inputs.handler import ai_model_node_input_handler
from src.runners.defs import observability_settings, project_root

# Add a root_id to the selected agent, as this will be the root component in this run
# This was intentionally not allowed to add to agent where it was defined inorder to reuse then if needed
root_component_id = "chatbot_root"  # Run records will be wrapped in a directory with this name
agent.root_id = root_component_id

# Create run context
run_context = RunContext(
    root_component_id=root_component_id,
    observability_settings=observability_settings,
    project_root=project_root,
    # input_source=project_root/"agents"/"chatbot"/"inputs"/"data", # Optional static input path
)

# Register the input handlers and static inputs
run_context.register_node_input_handler(ai_model_node_input_handler)
# run_context.register_input("initial_node", AIModelNodeInput(...)) #Optional Static Inputs


# Create a runner
runner = AgentRunner(agent, run_context)


# Now, to run this agent, there arre 2 options
# Either user dhenara cli to run this as in an isolated context
#
#   `dhenara run agent chatbot`
#
# OR
#
# Run directly like below
# For this option, you need to add the src directory path to PYTHONPATH


async def main():
    runner.setup_run()
    await runner.run()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
