import logging
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import ValidationError as PydanticValidationError

from dhenara.agent.dsl.base import ComponentDefinition
from dhenara.agent.dsl.components.agent import Agent, AgentExecutor
from dhenara.agent.dsl.components.flow import FlowExecutor
from dhenara.agent.dsl.inbuilt.registry import trace_registry  # noqa: F401 : For loading global registers
from dhenara.agent.observability import log_with_context
from dhenara.agent.observability.tracing import trace_method
from dhenara.agent.resource.registry import resource_config_registry
from dhenara.agent.run import RunContext
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)


class ComponentRunner(ABC):
    component_type: Literal["agent", "flow"] = None

    def __init__(self, agent: Agent, run_contex: RunContext):
        self.agent = agent
        self.run_context = run_contex
        self.logger = logging.getLogger(f"dhenara.dad.{self.component_type}.{self.agent.id}")
        logger.info(f"Initialized {self.__class__.__name__} with ID: {self.agent.id}")

    def set_previous_run_in_run_ctx(
        self,
        previous_run_id: str,
        agent_start_node_id: str | None = None,
        flow_start_node_id: str | None = None,
    ):
        # Update run context with rerun parameters if provided
        if previous_run_id or agent_start_node_id or flow_start_node_id:
            self.run_context.set_previous_run(
                previous_run_id=previous_run_id,
                agent_start_node_id=agent_start_node_id,
                flow_start_node_id=flow_start_node_id,
            )

    async def run(self):
        run_context: RunContext = self.run_context
        start_node_id = run_context.start_node_id

        log_with_context(
            self.logger,
            logging.INFO,
            f"Starting agent  {self.agent.id}",
            {"agent_id": str(self.agent.id)},
        )

        # Do run setup
        run_context.setup_run()

        # Copy input files from the previous run if this is a rerun
        if hasattr(run_context, "is_rerun") and run_context.is_rerun and run_context.previous_run_id:
            log_with_context(
                self.logger,
                logging.INFO,
                f"Rerunning from previous run {run_context.previous_run_id}"
                + (f" starting at node {start_node_id}" if start_node_id else ""),
                {
                    "agent_id": str(self.agent.id),
                    "previous_run_id": run_context.previous_run_id,
                    "start_node_id": start_node_id or "none",
                },
            )
        else:
            # Normal run, copy input files
            run_context.copy_input_files()

        run_context.read_static_inputs()

        try:
            await self.run_component()

            logger.debug("process_post: run completed")
            # Process and save results
            run_context.complete_run()

            log_with_context(
                self.logger,
                logging.INFO,
                f"Agent {self.agent.id} completed successfully",
                {"agent_id": str(self.agent.id)},
            )

            return True
        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Agent {self.agent.id} failed: {e!s}",
                {"agent_id": str(self.agent.id), "error": str(e)},
            )
            run_context.complete_run(status="failed")
            raise

    @abstractmethod
    @trace_method("run_component")
    async def run_component(self):
        pass

    # TODO_FUTURE: cleanup
    def get_resource_config(
        self,
        resource_profile="default",
    ):
        try:
            # Get resource configuration from registry
            resource_config = resource_config_registry.get(resource_profile)
            if not resource_config:
                # Fall back to creating a new one
                resource_config = self.load_default_resource_config()
                resource_config_registry.register(resource_profile, resource_config)

            return resource_config
        except Exception as e:
            raise ValueError(f"Error in resource setup: {e}")

    def load_default_resource_config(self):
        resource_config = ResourceConfig()
        resource_config.load_from_file(
            credentials_file="~/.env_keys/.dhenara_credentials.yaml",
            init_endpoints=True,
        )
        return resource_config


class FlowRunner(ComponentRunner):  # TODO: Not tested
    component_type = "flow"

    @trace_method("run_flow")
    async def run_component(self):
        flow_definition: ComponentDefinition = self.agent_node.flow
        run_context: RunContext = self.run_context

        try:
            # Create orchestrator with resolved resources
            executor = FlowExecutor(
                id=self.agent_id,  # TODO_FUTURE: Might need cleanup on multi agent flows
                definition=flow_definition,
                run_context=run_context,
            )

            # Execute the flow, potentially starting from a specific node
            _results = await executor.execute(
                resource_config=self.get_resource_config(),
                start_node_id=run_context.flow_start_node_id,
            )
            return _results

        except PydanticValidationError as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Invalid inputs: {e!s}",
                {"agent_id": str(self.agent_id), "error": str(e)},
            )
            raise DhenaraAPIError(f"Invalid Inputs {e}")


class AgentRunner(ComponentRunner):
    component_type = "agent"

    @trace_method("run_agent")
    async def run_component(self):
        agent_definition: ComponentDefinition = self.agent
        run_context: RunContext = self.run_context

        try:
            # Get resource configuration from registry

            # Create orchestrator with resolved resources
            executor = AgentExecutor(
                id=self.agent.id,  # TODO_FUTURE: Might need cleanup on multi agent agents
                definition=agent_definition,
                run_context=run_context,
            )

            # Execute the agent, potentially starting from a specific node
            _results = await executor.execute(
                resource_config=self.get_resource_config(),
                start_node_id=run_context.agent_start_node_id,
            )

            return _results

        except PydanticValidationError as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Invalid inputs: {e!s}",
                {"agent_id": str(self.agent.id), "error": str(e)},
            )
            raise DhenaraAPIError(f"Invalid Inputs {e}")
