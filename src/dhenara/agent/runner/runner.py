import logging
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import ValidationError as PydanticValidationError

from dhenara.agent.dsl.base import ComponentDefinition
from dhenara.agent.dsl.components.agent import Agent, AgentExecutor
from dhenara.agent.dsl.components.flow import Flow, FlowExecutor
from dhenara.agent.dsl.inbuilt.registry import trace_registry  # noqa: F401 : For loading global registers
from dhenara.agent.observability import log_with_context
from dhenara.agent.observability.tracing import trace_method
from dhenara.agent.run import RunContext
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)


class ComponentRunner(ABC):
    component_type: Literal["agent", "flow"] = None
    component_class = None

    def __init__(self, component: ComponentDefinition, run_contex: RunContext):
        if not isinstance(component, self.component_class):
            raise ValueError(
                f"component should be an instance of {type(self.component_class)}. component type is {type(component)}"
            )
        if component.root_id is None:
            raise ValueError("root_id should be set on root level ")

        self.component = component
        self.root_id = component.root_id
        self.run_context = run_contex
        self.logger = logging.getLogger(f"dhenara.dad.{self.component_type}.{self.root_id}")
        logger.info(f"Initialized {self.__class__.__name__} with ID: {self.root_id}")

    def setup_run(
        self,
        previous_run_id: str,
        agent_start_node_id: str | None = None,
        flow_start_node_id: str | None = None,
        run_id_prefix: str | None = None,
    ):
        # Update run context with rerun parameters if provided
        if previous_run_id or agent_start_node_id or flow_start_node_id:
            self.run_context.set_previous_run(
                previous_run_id=previous_run_id,
                agent_start_node_id=agent_start_node_id,
                flow_start_node_id=flow_start_node_id,
            )
            log_msg = f"Rerunning root {self.root_id} from revious run {self.run_context.previous_run_id}"
        else:
            log_msg = f"Running root {self.root_id} from begining with run_id {self.run_context.run_id}"
        # Setup run context
        self.run_context.setup_run(
            run_id_prefix=run_id_prefix,
        )

        # Normal run, copy input files
        if not self.run_context.is_rerun:
            self.run_context.copy_input_files()

        self.run_context.read_static_inputs()

        log_with_context(self.logger, logging.INFO, log_msg)

    async def run(self):
        try:
            log_with_context(
                self.logger,
                logging.INFO,
                f"{self.component_type.title()} {self.root_id} run begins",
                {
                    "component_type": self.component_type,
                    "root_id": self.root_id,
                    "agent_start_node_id": self.run_context.agent_start_node_id,
                    "flow_start_node_id": self.run_context.flow_start_node_id,
                },
            )

            await self.run_component()

            # Process and save results
            self.run_context.complete_run()

            log_with_context(
                self.logger,
                logging.INFO,
                f"Agent {self.root_id} completed successfully",
                {"agent_id": str(self.root_id)},
            )

            return True
        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Agent {self.root_id} failed: {e!s}",
                {"agent_id": str(self.root_id), "error": str(e)},
            )
            self.run_context.complete_run(status="failed")
            raise

    @abstractmethod
    @trace_method("run_component")
    async def run_component(self):
        pass


class FlowRunner(ComponentRunner):  # TODO: Not tested
    component_type = "flow"
    component_class = Flow

    @trace_method("run_flow")
    async def run_component(self):
        flow_definition = self.component
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
    component_class = Agent

    @trace_method("run_agent")
    async def run_component(self):
        agent_definition = self.component
        run_context: RunContext = self.run_context

        try:
            # Get resource configuration from registry

            # Create orchestrator with resolved resources
            executor = AgentExecutor(
                id=self.root_id,  # TODO_FUTURE: Might need cleanup on multi agent agents
                definition=agent_definition,
                run_context=run_context,
            )

            # Execute the agent, potentially starting from a specific node
            _results = await executor.execute(
                start_node_id=run_context.agent_start_node_id,
            )

            return _results

        except PydanticValidationError as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Invalid inputs: {e!s}",
                {"agent_id": str(self.root_id), "error": str(e)},
            )
            raise DhenaraAPIError(f"Invalid Inputs {e}")
