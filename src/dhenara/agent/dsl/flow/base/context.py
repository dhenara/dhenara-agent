import json
from asyncio import Event
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from dhenara.agent.dsl.base import ExecutionContext
from dhenara.agent.types.data import RunEnvParams
from dhenara.agent.types.flow import (
    FlowExecutionResults,
    FlowExecutionStatusEnum,
    FlowNodeExecutionResult,
    FlowNodeIdentifier,
    FlowNodeInput,
)
from dhenara.agent.utils.io.artifact_manager import ArtifactManager
from dhenara.ai.types.shared.base import BaseEnum, BaseModel


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


class FlowExecutionContext(ExecutionContext):
    """Execution context for a flow."""

    ##endpoint_id: str
    # flow_definition: FlowDefinition
    initial_inputs: dict[FlowNodeIdentifier, FlowNodeInput]
    execution_status: FlowExecutionStatusEnum = FlowExecutionStatusEnum.PENDING
    # current_node_index: int = 0
    current_node_identifier: FlowNodeIdentifier | None = None
    execution_results: FlowExecutionResults[Any] = {}
    execution_failed: bool = False
    execution_failed_message: str | None = None
    ## final_output: FlowNodeOutput : Not reuired as it can be found from execution_results
    metadata: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    streaming_contexts: dict[FlowNodeIdentifier, StreamingContext | None] = {}
    stream_generator: AsyncGenerator | None = None

    ## Build in callables
    artifact_manager: ArtifactManager | None = None
    run_env_params: RunEnvParams | None = None

    def create_iteration_context(self, iteration_data: dict[str, Any]) -> "ExecutionContext":
        """Create a new context for a loop iteration."""
        return ExecutionContext(initial_data=iteration_data, parent=self, artifact_manager=self.artifact_manager)

    async def record_outcome(self, node_def, result: Any) -> None:
        """Record the outcome of a node execution."""
        if not self.artifact_manager or not node_def.outcome_settings:
            return

        settings = node_def.outcome_settings
        if not settings.enabled:
            return

        # Resolve templates
        path = self.evaluate_template(settings.path_template)
        filename = self.evaluate_template(settings.filename_template)

        # Generate content
        if settings.content_template:
            content = self.evaluate_template(settings.content_template)
        else:
            # Default to JSON serialization
            if hasattr(result, "model_dump"):
                content = json.dumps(result.model_dump(), indent=2)
            else:
                content = json.dumps(result, indent=2, default=str)

        # Record the outcome
        commit_msg = None
        if settings.commit_message_template:
            commit_msg = self.evaluate_template(settings.commit_message_template)

        await self.artifact_manager.record_outcome(
            file_name=filename, path_in_repo=path, content=content, commit=settings.commit, commit_msg=commit_msg
        )

    async def record_iteration_outcome(self, loop_element, iteration: int, item: Any, result: Any) -> None:
        """Record the outcome of a loop iteration."""
        # Implementation depends on whether the loop has outcome settings
        # Similar to record_outcome but with iteration-specific values
        pass

    # -------------------------------------------------------------------------
    # TODO: legacy fns. clenaup
    # -------------------------------------------------------------------------

    def set_current_node(self, identifier: str):
        self.current_node_identifier = identifier

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

    def update_evaluation_context(self):  # TODO
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
