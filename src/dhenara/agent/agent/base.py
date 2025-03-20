import logging

from pydantic import ValidationError as PydanticValidationError

from dhenara.agent.dsl.agent import AgentNode
from dhenara.agent.dsl.base import ComponentDefinition
from dhenara.agent.dsl.flow import FlowExecutor
from dhenara.agent.resource.registry import resource_config_registry
from dhenara.agent.run import RunContext
from dhenara.agent.types import NodeInputs
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)


class BaseAgent:
    """{{agent_name}} agent implementation."""

    def __init__(self, agent_node: AgentNode):
        """Initialize the agent with optional configuration."""
        self.agent_node = agent_node
        # TODO: Configs?

        if not isinstance(self.agent_node, AgentNode):
            logger.error(
                f"Imported object is not an AgentNode: {type(self.agent_node)}"
            )
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

        logger.debug("process_post: run completed")
        # Process and save results
        run_context.complete_run()

        return True

    async def _run_flow(
        self,
        run_context: RunContext,
        initial_inputs: NodeInputs,
        resource_profile="default",
    ):
        flow_definition: ComponentDefinition = self.agent_node.flow

        try:
            # Get resource configuration from registry
            resource_config = resource_config_registry.get(resource_profile)
            if not resource_config:
                # Fall back to creating a new one
                resource_config = self.load_default_resource_config()
                resource_config_registry.register(resource_profile, resource_config)

            # Create orchestrator with resolved resources
            executor = FlowExecutor(
                definition=flow_definition,
                run_context=run_context,
            )
            # flow_orchestrator = FlowOrchestrator(
            #    flow_definition=flow_definition,
            #    resource_config=resource_config,
            # )

            # Execute
            # await flow_orchestrator.run(
            #    execution_context=execution_context,
            # )

            # Execute the flow
            _results = await executor.execute(
                # initial_data={"input_text": "Create a command-line tool that converts CSV to JSON"},
                initial_inputs=initial_inputs,
                resource_config=resource_config,
            )

            # TODO
            # if run_context.execution_context.execution_failed:
            #    logger.exception(f"Execution Failed: {run_context.execution_context.execution_failed_message}")
            #    return False

            ## Set `is_streaming` after execution returns
            # is_streaming = executor.definition.has_any_streaming_node()
            # if is_streaming:
            #    _response_stream_generator = execution_context.stream_generator
            # else:
            #    _response_data = {
            #        "execution_status": execution_context.execution_status,
            #        "execution_results": execution_context.execution_results,
            #    }

        except PydanticValidationError as e:
            raise DhenaraAPIError(f"Invalid Inputs {e}")

    def load_default_resource_config(self):
        resource_config = ResourceConfig()
        resource_config.load_from_file(
            credentials_file="~/.env_keys/.dhenara_credentials.yaml",
            init_endpoints=True,
        )
        return resource_config
