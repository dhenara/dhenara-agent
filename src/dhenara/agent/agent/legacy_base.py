import logging
from datetime import datetime

from pydantic import ValidationError as PydanticValidationError

from dhenara.agent.engine import FlowOrchestrator
from dhenara.agent.engine.types import LegacyFlowContext
from dhenara.agent.resource.registry import resource_config_registry
from dhenara.agent.run import RunContext
from dhenara.agent.types import Agent as AgentType
from dhenara.agent.types import FlowDefinition, NodeInputs
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)


class LegacyBaseAgent:
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
        initial_inputs: NodeInputs | None = None,
    ):
        # TODO: Bring inputs
        input_data = {
            "initial_inputs": initial_inputs,
        }
        input_files = []

        run_context.prepare_input(input_files)
        run_context.init_inputs(input_data)

        await self._run_flow(
            run_context=run_context,
            initial_inputs=run_context.initial_inputs,  # Pass the processed initial_inputs
        )

        # Process and save results
        run_context.complete_run()

        return True

    async def _run_flow(
        self,
        run_context: RunContext,
        initial_inputs: NodeInputs,
        resource_profile="default",
    ):
        flow_definition: FlowDefinition = self.agent_definition.flow_definition

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

            execution_context = LegacyFlowContext(
                flow_definition=flow_definition,
                initial_inputs=initial_inputs,
                created_at=datetime.now(),
                run_env_params=run_context.run_env_params,
                artifact_manager=run_context.artifact_manager,
            )

            # Initialize execution_context  in run_context
            run_context.execution_context = execution_context

            # Execute
            await flow_orchestrator.run(
                execution_context=execution_context,
            )

            # Set `is_streaming` after execution returns
            is_streaming = flow_orchestrator.flow_definition.has_any_streaming_node()

            if execution_context.execution_failed:
                logger.exception(f"Execution Failed: {execution_context.execution_failed_message}")
                return False

            if is_streaming:
                _response_stream_generator = execution_context.stream_generator
            else:
                _response_data = {
                    "execution_status": execution_context.execution_status,
                    "execution_results": execution_context.execution_results,
                }

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
