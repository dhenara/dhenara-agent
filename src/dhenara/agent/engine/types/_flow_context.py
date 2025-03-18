import logging
from asyncio import Event
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from pydantic import Field

from dhenara.agent.types.data import RunEnvParams
from dhenara.agent.types.flow import (
    FlowDefinition,
    FlowExecutionResults,
    FlowExecutionStatusEnum,
    FlowNodeExecutionResult,
    FlowNodeIdentifier,
    FlowNodeInput,
)
from dhenara.agent.utils.io.artifact_manager import ArtifactManager
from dhenara.ai.types.shared.base import BaseEnum, BaseModel

logger = logging.getLogger(__name__)


class StreamingStatusEnum(BaseEnum):
    NOT_STARTED = "not_started"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"


class StreamingContext(BaseModel):
    status: StreamingStatusEnum = StreamingStatusEnum.NOT_STARTED
    completion_event: Event | None = None
    result: FlowNodeExecutionResult | None = None
    error: Exception | None = None

    @property
    def successfull(self) -> bool:
        return self.status == StreamingStatusEnum.COMPLETED


class LoopState(BaseModel):
    """State for loop execution."""

    iteration: int = 0
    item: Any = None
    # iteration_results: list[dict[str, Any]] = Field(default_factory=list)
    iteration_results: list[dict[FlowNodeIdentifier, FlowNodeExecutionResult]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    continue_loop: bool = True


class EvaluationContext(BaseModel):
    """Context for expression evaluation."""

    variables: dict[str, Any] = Field(default_factory=dict)

    def evaluate(self, expression: str) -> Any:
        """Evaluate an expression using the context."""
        # Create a safe evaluation environment
        safe_builtins = {
            "len": len,
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "sum": sum,
            "min": min,
            "max": max,
            "any": any,
            "all": all,
        }

        eval_globals = {
            "__builtins__": safe_builtins,
        }

        try:
            return eval(expression, eval_globals, self.variables)
        except Exception as e:
            logger.error(f"Error evaluating expression '{expression}': {e}")
            raise ValueError(f"Expression evaluation failed: {e}")


class FlowContext(BaseModel):
    # endpoint_id: str
    flow_definition: FlowDefinition
    initial_inputs: dict[FlowNodeIdentifier, FlowNodeInput]
    execution_status: FlowExecutionStatusEnum = FlowExecutionStatusEnum.PENDING
    current_node_index: int = 0
    current_node_identifier: FlowNodeIdentifier | None = None
    execution_results: FlowExecutionResults[Any] = {}
    execution_failed: bool = False
    execution_failed_message: str | None = None
    # final_output: FlowNodeOutput : Not reuired as it can be found from execution_results
    metadata: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    streaming_contexts: dict[FlowNodeIdentifier, StreamingContext | None] = {}
    stream_generator: AsyncGenerator | None = None

    # Build in callables
    artifact_manager: ArtifactManager | None = None
    run_env_params: RunEnvParams | None = None

    # fields for control flow
    # loop_states: dict[str, LoopState] = Field(default_factory=dict)
    loop_states: dict[FlowNodeIdentifier, LoopState] = Field(default_factory=dict)
    current_subflow_path: list[str] = Field(default_factory=list)
    evaluation_context: EvaluationContext = Field(default_factory=EvaluationContext)

    def set_current_node(self, index: int):
        self.current_node_index = index
        self.current_node_identifier = self.flow_definition.nodes[index].identifier

    def get_initial_input(self) -> FlowNodeInput:
        if not self.current_node_identifier:
            raise ValueError("get_initial_input: current_node_identifier is not set")

        return self.initial_inputs.get(self.current_node_identifier, None)

    async def notify_streaming_complete(
        self,
        identifier: FlowNodeIdentifier,
        streaming_status: StreamingStatusEnum,
        result: FlowNodeExecutionResult,
    ) -> None:
        streaming_context = self.streaming_contexts[identifier]
        if not streaming_context:
            raise ValueError(f"notify_streaming_complete: Failed to get streaming_context for id {identifier}")

        streaming_context.status = streaming_status
        streaming_context.result = result
        self.execution_results[identifier] = result
        streaming_context.completion_event.set()

    def get_current_subflow_id(self) -> str:
        """Get the ID for the current subflow path."""
        return ".".join(self.current_subflow_path) if self.current_subflow_path else "main"

    def push_subflow(self, name: str):
        """Add a subflow to the current path."""
        self.current_subflow_path.append(name)

    def pop_subflow(self):
        """Remove the last subflow from the path."""
        if self.current_subflow_path:
            return self.current_subflow_path.pop()
        return None

    def start_loop(self, loop_id: str) -> LoopState:
        """Initialize a new loop state."""
        full_id = f"{self.get_current_subflow_id()}.{loop_id}"
        state = LoopState()
        self.loop_states[full_id] = state
        return state

    def get_loop_state(self, loop_id: str) -> LoopState:
        """Get the loop state for a given ID."""
        full_id = f"{self.get_current_subflow_id()}.{loop_id}"
        return self.loop_states.get(full_id)

    def update_evaluation_context(self):
        """Update evaluation context with current execution results and state."""
        # Add execution results to context
        for node_id, result in self.execution_results.items():
            if result.node_output and result.node_output.data:
                key = f"node_output.{node_id}"
                self.evaluation_context.variables[key] = result.node_output.data

                # Use shorter alias for results
                self.evaluation_context.variables[node_id] = result.node_output.data

        # Add loop states if available
        for loop_id, state in self.loop_states.items():
            self.evaluation_context.variables[f"loop.{loop_id}"] = {
                "iteration": state.iteration,
                "item": state.item,
                "results": state.iteration_results,
                "context": state.context,
            }

        # Add run environment parameters
        if self.run_env_params:
            env_vars = self.run_env_params.get_template_variables()
            for key, value in env_vars.items():
                self.evaluation_context.variables[key] = value
