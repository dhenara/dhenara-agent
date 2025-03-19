import json
import logging
from typing import Any

from dhenara.agent.dsl.base import ExecutionContext


class FlowExecutionContext(ExecutionContext):
    """Execution context for a flow."""

    # endpoint_id: str
    # flow_definition: FlowDefinition
    # initial_inputs: dict[FlowNodeIdentifier, FlowNodeInput]
    # execution_status: FlowExecutionStatusEnum = FlowExecutionStatusEnum.PENDING
    # current_node_index: int = 0
    # current_node_identifier: FlowNodeIdentifier | None = None
    # execution_results: FlowExecutionResults[Any] = {}
    # execution_failed: bool = False
    # execution_failed_message: str | None = None
    ## final_output: FlowNodeOutput : Not reuired as it can be found from execution_results
    # metadata: dict[str, Any] = {}
    # created_at: datetime
    # updated_at: datetime | None = None
    # completed_at: datetime | None = None
    # streaming_contexts: dict[FlowNodeIdentifier, StreamingContext | None] = {}
    # stream_generator: AsyncGenerator | None = None

    ## Build in callables
    # artifact_manager: ArtifactManager | None = None
    # run_env_params: RunEnvParams | None = None

    ## fields for control flow
    ## loop_states: dict[str, LoopState] = Field(default_factory=dict)
    # loop_states: dict[FlowNodeIdentifier, LoopState] = Field(default_factory=dict)
    # current_subflow_path: list[str] = Field(default_factory=list)
    # evaluation_context: EvaluationContext = Field(default_factory=EvaluationContext)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger("dhenara.agent.flow")

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
