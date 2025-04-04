import logging
from typing import ClassVar

from pydantic import ValidationError as PydanticValidationError

from dhenara.agent.dsl.agent import AgentNode
from dhenara.agent.dsl.base import ComponentDefinition, NodeID
from dhenara.agent.dsl.flow import FlowExecutor
from dhenara.agent.dsl.inbuilt.registry import trace_registry  # noqa: F401 : For loading global registers
from dhenara.agent.observability import log_with_context
from dhenara.agent.observability.tracing import trace_method
from dhenara.agent.resource.registry import resource_config_registry
from dhenara.agent.run import RunContext
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)


class AgentMeta(type):
    """Metaclass to enforce required class attributes in Agent subclasses."""

    def __new__(mcs, name, bases, namespace):
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
        self.logger = logging.getLogger(f"dhenara.agent.{self.agent_id}")
        logger.info(f"Initialized {self.__class__.__name__} with ID: {self.agent_id}")

    @trace_method("run_agent")
    async def run(
        self,
        run_context: RunContext,
        start_node_id: str | None = None,
    ):
        log_with_context(self.logger, logging.INFO, f"Starting agent {self.agent_id}", {"agent_id": str(self.agent_id)})

        # Copy input files from the previous run if this is a rerun
        if hasattr(run_context, "is_rerun") and run_context.is_rerun and run_context.previous_run_id:
            log_with_context(
                self.logger,
                logging.INFO,
                f"Rerunning from previous run {run_context.previous_run_id}"
                + (f" starting at node {start_node_id}" if start_node_id else ""),
                {
                    "agent_id": str(self.agent_id),
                    "previous_run_id": run_context.previous_run_id,
                    "start_node_id": start_node_id or "none",
                },
            )
        else:
            # Normal run, copy input files
            run_context.copy_input_files()

        run_context.read_static_inputs()

        try:
            await self._run_flow(
                run_context=run_context,
                start_node_id=start_node_id or getattr(run_context, "start_node_id", None),
            )

            logger.debug("process_post: run completed")
            # Process and save results
            run_context.complete_run()

            log_with_context(
                self.logger,
                logging.INFO,
                f"Agent {self.agent_id} completed successfully",
                {"agent_id": str(self.agent_id)},
            )

            return True
        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Agent {self.agent_id} failed: {e!s}",
                {"agent_id": str(self.agent_id), "error": str(e)},
            )
            run_context.complete_run(status="failed")
            raise

    @trace_method("run_flow")
    async def _run_flow(
        self,
        run_context: RunContext,
        resource_profile="default",
        start_node_id: str | None = None,
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

            # Execute the flow, potentially starting from a specific node
            _results = await executor.execute(
                resource_config=resource_config,
                start_node_id=start_node_id,
            )

        except PydanticValidationError as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Invalid inputs: {e!s}",
                {"agent_id": str(self.agent_id), "error": str(e)},
            )
            raise DhenaraAPIError(f"Invalid Inputs {e}")

    def load_default_resource_config(self):
        resource_config = ResourceConfig()
        resource_config.load_from_file(
            credentials_file="~/.env_keys/.dhenara_credentials.yaml",
            init_endpoints=True,
        )
        return resource_config
