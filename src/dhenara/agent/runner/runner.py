import logging
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import ValidationError as PydanticValidationError

from dhenara.agent.dsl.base import ComponentDefinition
from dhenara.agent.dsl.components.agent import Agent, AgentDefinition
from dhenara.agent.dsl.components.flow import Flow, FlowDefinition
from dhenara.agent.observability import log_with_context
from dhenara.agent.observability.tracing import trace_method
from dhenara.agent.run import RunContext
from dhenara.agent.types import AgentRunConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError

# INFO: Import any registreis here to loading global registers

logger = logging.getLogger(__name__)


class ComponentRunner(ABC):
    executable_type: Literal["agent", "flow"] = None
    component_def_class = None

    def __init__(self, component_def: ComponentDefinition, run_contex: RunContext, root_id: str | None = None):
        if not isinstance(component_def, self.component_def_class):
            raise ValueError(
                f"component should be an instance of {type(self.component_def_class)} not type of {type(component_def)}"
            )
        root_id = root_id or component_def.root_id
        if root_id is None:
            raise ValueError("root_id should be set on root level ")

        self.component_def = component_def
        self.root_id = root_id
        self.run_context = run_contex
        self.logger = logging.getLogger(f"dhenara.dad.{self.executable_type}.{self.root_id}")
        logger.info(f"Initialized {self.__class__.__name__} with ID: {self.root_id}")

    def setup_run(self, run_config: AgentRunConfig):
        # Update run context with rerun parameters if provided
        if run_config.previous_run_id or run_config.start_hierarchy_path:
            self.run_context.set_previous_run(
                previous_run_id=run_config.previous_run_id,
                start_hierarchy_path=run_config.start_hierarchy_path,
            )
            log_msg = f"Rerunning root {self.root_id} from previous run {self.run_context.previous_run_id}"
            if run_config.start_hierarchy_path:
                log_msg += f" starting from {run_config.start_hierarchy_path}"
        else:
            log_msg = f"Running root {self.root_id} from beginning with run_id {self.run_context.run_id}"

        # Setup run context
        self.run_context.setup_run(
            run_config=run_config,
        )

        # Normal run, copy input files
        if not self.run_context.is_rerun:
            self.run_context.copy_input_files()
        self.run_context.read_static_inputs()
        log_with_context(self.logger, logging.INFO, log_msg)

    async def run(self):
        try:
            _logattributes = {
                "executable_type": self.executable_type,
                "root_id": self.root_id,
            }
            if self.run_context.start_hierarchy_path:
                _logattributes["start_hierarchy_path"] = self.run_context.start_hierarchy_path

            log_with_context(
                self.logger,
                logging.INFO,
                f"{self.executable_type.title()} {self.root_id} run begins",
                _logattributes,
            )

            await self.run_component()

            # Process and save results
            await self.run_context.complete_run()

            log_with_context(
                self.logger,
                logging.INFO,
                f"Agent {self.root_id} completed successfully",
                {"root_id": str(self.root_id)},
            )

            return True
        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Agent {self.root_id} failed: {e!s}",
                {"root_id": str(self.root_id), "error": str(e)},
            )
            await self.run_context.complete_run(status="failed")
            raise

    @abstractmethod
    @trace_method("run_component")
    async def run_component(self):
        pass


class FlowRunner(ComponentRunner):  # Not tested
    executable_type = "flow"
    component_def_class = FlowDefinition

    @trace_method("run_flow")
    async def run_component(self):
        run_context: RunContext = self.run_context

        try:
            flow = Flow(
                id=self.root_id,
                definition=self.component_def,
            )

            _results = await flow.execute(
                execution_context=None,  # Set as the root
                run_context=run_context,
            )

            return _results

        except PydanticValidationError as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Invalid inputs: {e!s}",
                {"root_id": str(self.root_id), "error": str(e)},
            )
            raise DhenaraAPIError(f"Invalid Inputs {e}")


class AgentRunner(ComponentRunner):
    executable_type = "agent"
    component_def_class = AgentDefinition

    @trace_method("run_agent")
    async def run_component(self):
        run_context: RunContext = self.run_context

        try:
            agent = Agent(
                id=self.root_id,
                definition=self.component_def,
            )

            _results = await agent.execute(
                execution_context=None,  # Set as the root
                run_context=run_context,
            )

            return _results

        except PydanticValidationError as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Invalid inputs: {e!s}",
                {"root_id": str(self.root_id), "error": str(e)},
            )
            raise DhenaraAPIError(f"Invalid Inputs {e}")
