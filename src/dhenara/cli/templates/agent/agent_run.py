import logging

from dhenara.agent.observability import ObservabilitySettings
from dhenara.agent.run import RunContext
from dhenara.agent.shared.utils import find_project_root

from .agent import MyAgent
from .inputs.handler import ai_model_input_handler

# Set up observability with console exporter
observability_settings = ObservabilitySettings(
    service_name="my-agent-service",
    tracing_exporter_type="zipkin",  # "console", "file", "otlp", "jaeger", "zipkin"
    metrics_exporter_type="file",  # "console", "file", "otlp"
    logging_exporter_type="file",  # "console", "file", "otlp"
    root_log_level=logging.DEBUG,
)

# Initialize the agent
agent = MyAgent()

# Find project root directory
project_root = find_project_root()
if not project_root:
    print("Error: Not in a Dhenara project directory.")

# Create run context
run_context = RunContext(
    project_root=project_root,
    agent_identifier=agent.agent_id,
    observability_settings=observability_settings,
)
# Register the handler
run_context.register_node_input_handler(ai_model_input_handler)

## Optionally Register static inputs for specific nodes
# run_context.register_input("initial_node", AIModelNodeInput(...))

## Run the agent
# await agent.run(run_context)
