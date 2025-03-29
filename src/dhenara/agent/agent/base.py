import logging
from typing import ClassVar

from pydantic import ValidationError as PydanticValidationError

from dhenara.agent.dsl.agent import AgentNode
from dhenara.agent.dsl.base import ComponentDefinition, NodeID
from dhenara.agent.dsl.flow import FlowExecutor
from dhenara.agent.resource.registry import resource_config_registry
from dhenara.agent.run import RunContext
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)


class AgentMeta(type):
    """Metaclass to enforce required class attributes in Agent subclasses."""

    def __new__(mcs, name, bases, namespace):  # noqa: N804
        cls = super().__new__(mcs, name, bases, namespace)

        # Skip validation for the BaseAgent class itself
        if name == "BaseAgent":
            return cls

        # Check for required class attributes
        if not hasattr(cls, "agent_id"):  # or not isinstance(cls.agent_id, NodeID):
            raise TypeError(f"Class {name} must define a class attribute 'agent_id' of type NodeID")

        if not hasattr(cls, "agent_node") or not isinstance(cls.agent_node, AgentNode):
            raise TypeError(f"Class {name} must define a class attribute 'agent_node' of type AgentNode")

        return cls


class BaseAgent(metaclass=AgentMeta):
    """{{agent_name}} agent implementation."""

    # Define these as class variables with type annotations
    agent_id: ClassVar[NodeID]
    agent_node: ClassVar[AgentNode]

    def __init__(self):
        """Initialize the agent with the class-defined configuration."""
        logger.info(f"Initialized {self.__class__.__name__} with ID: {self.agent_id}")

    async def run(
        self,
        run_context: RunContext,
    ):
        run_context.copy_input_files()
        run_context.read_static_inputs()

        await self._run_flow(
            run_context=run_context,
        )

        logger.debug("process_post: run completed")
        # Process and save results
        run_context.complete_run()

        return True

    async def _run_flow(
        self,
        run_context: RunContext,
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
                id=self.agent_id,  # TODO_FUTURE: Might need cleanup on multi agent flows
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
