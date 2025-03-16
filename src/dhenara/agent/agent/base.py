import logging
from datetime import datetime

from pydantic import ValidationError as PydanticValidationError

from dhenara.agent.engine import FlowOrchestrator
from dhenara.agent.resource.registry import resource_config_registry
from dhenara.agent.run import RunContext
from dhenara.agent.types import (
    Agent as AgentType,
)
from dhenara.agent.types import (
    FlowContext,
    FlowDefinition,
    FlowNodeInputs,
)
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)


class BaseAgent:
    """{{agent_name}} agent implementation."""

    def __init__(self, agent_definition):
        """Initialize the agent with optional configuration."""
        self.agent_definition = agent_definition
        # TODO: Configs?

        if not isinstance(self.agent_definition, AgentType):
            logger.error(f"Imported object is not a AgentType: {type(self.agent_definition)}")
            return

    async def run(
        self,
        run_context: RunContext,
        initial_inputs: FlowNodeInputs | None = None,
    ):
        # TODO: Bring inputs
        input_data = {
            "initial_inputs": initial_inputs,
        }
        input_files = []

        run_context.prepare_input(input_data, input_files)

        await self._run_flow(
            flow_definition=self.agent_definition.flow_definition,
            initial_inputs=run_context.initial_inputs,  # Pass the processed initial_inputs
        )

        return {"response": "Processed: "}

    async def _run_flow(
        self,
        flow_definition: FlowDefinition,
        initial_inputs: FlowNodeInputs,
        resource_profile="default",
    ):
        try:
            # Get resource configuration from registry
            resource_config = resource_config_registry.get(resource_profile)
            if not resource_config:
                # Fall back to creating a new one
                resource_config = self.load_default_resource_config()
                resource_config_registry.register(resource_profile, resource_config)

            # Create orchestrator with resolved resources
            flow_orchestrator = FlowOrchestrator(
                flow_definition=flow_definition,
                resource_config=resource_config,
            )

            flow_context = FlowContext(
                flow_definition=flow_definition,
                initial_inputs=initial_inputs,
                created_at=datetime.now(),
            )

            # Execute
            await flow_orchestrator.run(flow_context)

            # Set `is_streaming` after execution returns
            is_streaming = flow_orchestrator.flow_definition.has_any_streaming_node()

            if flow_context.execution_failed:
                logger.exception(f"Execution Failed: {flow_context.execution_failed_message}")
                return False

            if is_streaming:
                response_stream_generator = flow_context.stream_generator
                print(f"Steam generator is: {response_stream_generator}")
            else:
                response_data = {
                    "execution_status": flow_context.execution_status,
                    "execution_results": flow_context.execution_results,
                }
                print(f"response_data: {response_data}")

        except PydanticValidationError as e:
            raise DhenaraAPIError(f"Invalid Inputs {e}")

        logger.debug("process_post: run completed")

    def load_default_resource_config(self):
        resource_config = ResourceConfig()
        resource_config.load_from_file(
            credentials_file="~/.env_keys/.dhenara_credentials.yaml",
            init_endpoints=True,
        )
        return resource_config
