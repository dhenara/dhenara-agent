import json
import logging
from asyncio import Event
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, ClassVar, Optional, TypeVar

from pydantic import Field

from dhenara.agent.dsl.base.node.node_exe_result import (
    NodeExecutionResult,
    NodeInputT,
    NodeOutcomeT,
    NodeOutputT,
)
from dhenara.agent.dsl.base.node.node_io import NodeInput
from dhenara.agent.dsl.base.utils import NodeHierarchyHelper
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseEnum, BaseModel, BaseModelABC
from dhenara.agent.utils.io.artifact_manager import ArtifactManager
from dhenara.ai.types.resource import ResourceConfig

from .defs import NodeID
from .enums import ExecutableTypeEnum, ExecutionStatusEnum


class StreamingStatusEnum(BaseEnum):
    NOT_STARTED = "not_started"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"


class StreamingContext(BaseModel):
    status: StreamingStatusEnum = StreamingStatusEnum.NOT_STARTED
    completion_event: Event | None = None
    result: NodeExecutionResult | None = None
    error: Exception | None = None

    @property
    def successfull(self) -> bool:
        return self.status == StreamingStatusEnum.COMPLETED


class ExecutionContext(BaseModelABC):
    """A generic execution context for any DSL execution."""

    # INFO: Cannot add typehint as its hard to resolve import erros
    # It is not necessary to fix this soon as the execution context is used at runtime

    executable_type: ExecutableTypeEnum = Field(...)
    component_id: NodeID  # TODO: Cehck if this is needed
    component_definition: Any  # Type of ComponentDefinition

    # Core data structures
    parent: Optional["ExecutionContext"] = Field(default=None)

    # Flow-specific tracking
    current_node_identifier: NodeID | None = Field(default=None)

    # TODO_FUTURE: An option to statically override node settings
    # initial_inputs: NodeInputs = Field(default_factory=dict)

    execution_status: ExecutionStatusEnum = Field(default=ExecutionStatusEnum.PENDING)
    execution_results: dict[
        NodeID,
        NodeExecutionResult[
            NodeInputT,
            NodeOutputT,
            NodeOutcomeT,
        ],
    ] = Field(default_factory=dict)
    execution_failed: bool = Field(default=False)
    execution_failed_message: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Streaming support
    streaming_contexts: dict[NodeID, StreamingContext | None] = Field(default_factory=dict)
    stream_generator: AsyncGenerator | None = Field(default=None)

    # Environment
    run_context: RunContext

    # Logging
    logger: ClassVar = logging.getLogger("dhenara.dad.execution_ctx")

    # TODO: Enable event bus
    # event_bus: EventBus = Field(default_factory=EventBus)
    # async def publish_event(self, event_type: str, data: Any):
    #    """Publish an event from the current node"""
    #    await self.event_bus.publish(
    #        event_type, data, self.current_node_identifier
    #    )

    @property
    def resource_config(self) -> ResourceConfig:
        return self.run_context.resource_config

    @property
    def artifact_manager(self) -> ArtifactManager:
        return self.run_context.artifact_manager

    @property
    def start_id(self) -> ResourceConfig:
        if self.executable_type == ExecutableTypeEnum.flow_node:
            return self.run_context.start_id_flow_node
        elif self.executable_type == ExecutableTypeEnum.flow:
            return self.run_context.start_id_flow
        elif self.executable_type == ExecutableTypeEnum.agent:
            return self.run_context.start_id_agent
        else:
            raise ValueError(f"start_id: Unsupported executable type: {self.executable_type}")

    def get_value(self, path: str) -> Any:
        """Get a value from the context by path."""
        # Handle simple keys
        if "." not in path:
            if path in self.data:
                return self.data[path]
            if path in self.results:
                return self.results[path]
            if self.parent:
                return self.parent.get_value(path)
            return None

        # Handle nested paths
        parts = path.split(".")
        current = self.get_value(parts[0])

        for part in parts[1:]:
            if current is None:
                return None

            # Handle list indexing
            if isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            # Handle dictionary access
            elif isinstance(current, dict) and part in current:
                current = current[part]
            # Handle object attribute access
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current

    def set_result(
        self,
        node_id: NodeID,
        result: NodeExecutionResult,
    ):
        """Set a result value in the context."""
        self.execution_results[node_id] = result
        self.updated_at = datetime.now()

    def set_execution_failed(self, message: str) -> None:
        """Mark execution as failed with a message."""
        self.execution_failed = True
        self.execution_failed_message = message
        self.execution_status = ExecutionStatusEnum.FAILED
        self.logger.error(f"Execution failed: {message}")

    # Node specific methods
    def set_current_node(self, identifier: str):
        """Set the current node being executed."""
        self.current_node_identifier = identifier

    def get_initial_input(self) -> NodeInput:
        """Get the input for the current node."""
        if not self.current_node_identifier:
            raise ValueError("get_initial_input: current_node_identifier is not set")

        # TODO
        # input_data = self.initial_inputs.get(self.current_node_identifier, None)
        # if isinstance(input_data, NodeInput):
        #     return input_data
        # elif isinstance(input_data, dict):
        #     return NodeInput(**input_data)
        # else:
        #     return None

    async def notify_streaming_complete(
        self,
        identifier: NodeID,
        streaming_status: StreamingStatusEnum,
        result: NodeExecutionResult,
    ) -> None:
        streaming_context = self.streaming_contexts[identifier]
        if not streaming_context:
            raise ValueError(f"notify_streaming_complete: Failed to get streaming_context for id {identifier}")

        streaming_context.status = streaming_status
        streaming_context.result = result
        self.execution_results[identifier] = result
        streaming_context.completion_event.set()

    # ------------: TODO: Review
    def create_iteration_context(self, iteration_data: dict[str, Any]) -> "ExecutionContext":
        """Create a new context for a loop iteration."""
        return ExecutionContext(
            initial_data=iteration_data,
            parent=self,
            artifact_manager=self.artifact_manager,
        )

    def merge_iteration_context(self, iteration_context: "ExecutionContext") -> None:
        """Merge results from an iteration context back to this context."""
        for key, value in iteration_context.results.items():
            iteration_key = f"{key}_{len([k for k in self.results if k.startswith(key + '_')])}"
            self.results[iteration_key] = value

    def create_conditional_context(self, condition_data: dict[str, Any]) -> "ExecutionContext":
        """Create a context for a conditional branch."""
        conditional_context = self.model_copy(deep=True)
        conditional_context.metadata.update(condition_data)
        return conditional_context

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
            file_name=filename,
            path_in_repo=path,
            content=content,
            commit=settings.commit,
            commit_msg=commit_msg,
        )

    async def record_iteration_outcome(self, loop_element, iteration: int, item: Any, result: Any) -> None:
        """Record the outcome of a loop iteration."""
        # Implementation depends on whether the loop has outcome settings
        # Similar to record_outcome but with iteration-specific values
        pass

    def get_node_hierarchy_path(self) -> str:
        """
        Get the hierarchical path of the current node within the flow.

        Returns:
            A path string representing the node's hierarchy (e.g., "main_flow/subflow1/node_id")
        """
        if not self.current_node_identifier:
            return ""

        return NodeHierarchyHelper.get_node_hierarchy_path(
            execution_context=self,
            node_id=self.current_node_identifier,
        )

    def get_dad_dynamic_variables(self) -> dict:
        return {
            "node_id": self.current_node_identifier,
            "node_hier": self.get_node_hierarchy_path(),
        }

    def evaluate_expression(self, expression: str) -> Any:
        """Evaluate an expression using the context's state."""
        from .data.dad_template_engine import DADTemplateEngine

        run_env_params = self.run_context.run_env_params
        dad_dynamic_variables = self.get_dad_dynamic_variables()
        return DADTemplateEngine.render_dad_template(
            template=expression,
            variables={},
            dad_dynamic_variables=dad_dynamic_variables,
            run_env_params=run_env_params,
            node_execution_results=None,
        )


ContextT = TypeVar("ContextT", bound=ExecutionContext)
