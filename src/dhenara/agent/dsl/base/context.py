import json
import logging
import os
import uuid
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
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseEnum, BaseModel, BaseModelABC
from dhenara.agent.utils.io.artifact_manager import ArtifactManager
from dhenara.ai.types.resource import ResourceConfig

from .defs import NodeID
from .enums import ControlBlockTypeEnum, ExecutableTypeEnum, ExecutionStatusEnum


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
    control_block_type: ControlBlockTypeEnum | None = Field(default=None)
    component_id: NodeID
    component_definition: Any  # Type of ComponentDefinition
    context_id: uuid.UUID = Field(default_factory=uuid.uuid4)

    # Core data structures
    parent: Optional["ExecutionContext"] = Field(default=None)

    # Flow-specific tracking
    # current_element_identifiers
    current_node_identifier: NodeID | None = Field(default=None)
    current_subcomponent_identifier: NodeID | None = Field(default=None)

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

    # Additional template rendering variables
    component_variables: dict[str, Any] = Field(default_factory=dict)  # Variables defined in component definition
    iteration_variables: dict[str, Any] = Field(default_factory=dict)

    # Streaming support
    streaming_contexts: dict[NodeID, StreamingContext | None] = Field(default_factory=dict)
    stream_generator: AsyncGenerator | None = Field(default=None)

    # Environment
    run_context: RunContext

    # Logging
    logger: ClassVar = logging.getLogger("dhenara.dad.execution_ctx")

    # TODO_FUTURE: Enable event bus
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
    def start_hierarchy_path(self) -> ResourceConfig:
        return self.run_context.start_hierarchy_path

    @property
    def hierarchy_path(self) -> ResourceConfig:
        return self.get_hierarchy_path(path_joiner=".")

    @property
    def current_element_identifier(self):
        return self.current_node_identifier if self.current_node_identifier else self.current_subcomponent_identifier

    def set_current_node(self, identifier: str):
        """Set the current node being executed."""
        self.current_node_identifier = identifier
        self.current_subcomponent_identifier = None

    def set_current_subcomponent(self, identifier: str):
        self.current_node_identifier = None
        self.current_subcomponent_identifier = identifier

    def model_post_init(self, __context: Any) -> None:
        """Register this context after initialization."""
        self.run_context.execution_context_registry.register(self)

    def get_children(self) -> list["ExecutionContext"]:
        """Get all children of this context."""
        return self.run_context.execution_context_registry.get_children(self)

    @property
    def should_execute(self) -> bool:
        """
        Determine if the current node should be executed based on the start_hierarchy_path.
        This is used to skip nodes that are not part of the current execution path.

        NOTE: The return value should be cached while using as calling this will reset the start_hierarchy_path
        in the run context when the current node is the start node.
        """
        # No start hierarchy path, execute normally
        start_hierarchy_path = self.run_context.start_hierarchy_path
        if not start_hierarchy_path:
            return True

        current_context_hierarchy_path = self.get_hierarchy_path(path_joiner=".")

        if current_context_hierarchy_path.endswith(start_hierarchy_path):
            # This is exactly where we want to start, so clear the flag
            self.run_context.start_hierarchy_path = None
            should_execute = True
        else:
            # Need to continue down to the target
            should_execute = False

        return should_execute

    async def load_from_previous_run(
        self,
        copy_artifacts: bool = True,
        element_id: NodeID | None = None,
    ) -> dict | None:
        hierarchy_path = self.get_hierarchy_path(
            path_joiner=os.sep,
            element_id=element_id,
        )

        result_data = await self.run_context.load_from_previous_run(
            hierarchy_path=hierarchy_path,
            copy_artifacts=copy_artifacts,
            is_component=True if self.executable_type != ExecutableTypeEnum.flow_node is None else False,
        )
        return result_data

    def get_hierarchy_path(
        self,
        path_joiner: str = "/",
        element_id: NodeID | None = None,
        exclude_element_id: bool = False,
    ) -> str:
        """
        Determine the hierarchical path of an element (node/sub-component) within a component definition.
        """

        component_path_parts = self.find_parent_component_ids()

        if exclude_element_id:
            final_path_parts = [*component_path_parts]
        else:
            if not element_id:
                # If no element_id is provided, use the current node identifier
                element_id = self.current_element_identifier

            # if not element_id:
            #    raise ValueError("get_hierarchy_path: element_id is None when exclude_element_id is not set")

        if element_id:
            final_path_parts = [*component_path_parts, element_id]
        else:
            final_path_parts = [*component_path_parts]

        try:
            return path_joiner.join(final_path_parts)
        except Exception as e:
            raise ValueError(f"get_hierarchy_path: Error: {e}")

    def find_parent_component_ids(self) -> list[str]:
        comp_path_parts = [self.component_id]

        parent_ctx = self.parent
        while parent_ctx is not None:
            comp_path_parts.append(parent_ctx.component_id)
            parent_ctx = parent_ctx.parent

        comp_path_parts.reverse()  # Reverse the order
        return comp_path_parts

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

    def get_initial_input(self) -> NodeInput:
        """Get the input for the current node."""
        if not self.current_node_identifier:
            raise ValueError("get_initial_input: current_node_identifier is not set")

        # TODO_FUTURE
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

    def get_dad_template_dynamic_variables(self) -> dict:
        # Update CURRENT component/ element/ hier
        # NOTE: These are used to derived the artifact record's name/dir via NodeRecordSettings

        return {
            # "component_id": str(self.component_id),
            "element_id": str(self.current_element_identifier),
            "element_hier_path": self.get_hierarchy_path(path_joiner=os.sep),
            "component_hier_path": self.get_hierarchy_path(path_joiner=os.sep, exclude_element_id=True),
        }

    def get_component_variables(self) -> dict:
        # These are just like dynamic variables. Should NOT be resolved hierarchicaly
        return self.component_variables

    def get_control_block_immediate_parent_variables(self) -> dict:
        #  `Control` blocks need to get variables from parent their immediate parent
        # as they doesn't hold any variables inside thier definition.
        # This is required for flow intutive var definitions like
        #
        # --        multi_image_flow = FlowDefinition()
        # --        multi_image_flow.vars(
        # --            {
        # --                "image_task": PLACEHOLDER,
        # --            }
        # --        )
        # --        multi_image_flow.for_each(
        # --            id="image_gen_loop",
        # --            statement="$expr{image_task.task_specifications}",
        # --            item_var="task_spec",
        # --            max_iterations=10,
        # --            body=single_img_flow,
        # --        )
        #
        #

        # TODO: Fix Below
        #
        # Currently, with Control Blocks, there will be 2 layers of `unwanted` execution-contexts created
        # One from the subcomponent execute() and then from the control-block execute()
        # Therefor below check will not satify for the first level context
        #   --  if self.control_block_type is not None and self.parent:
        # and parent variable won't be processed as expected
        # This need to be addressed with proper context handling.
        # NOTE: This might also have a side effect in get_control_block_hierarchical_parent_variables() too.

        if self.parent:
            return self.parent.get_component_variables()
        return {}

    def get_control_block_hierarchical_parent_variables(self) -> dict[str, Any]:
        """
        Collect component_variables from all control block parents in the execution hierarchy.

        Traverses up the parent chain, gathering variables from any parent that's a control block.
        When the same variable exists in multiple parents, the closest parent's value takes precedence.

        Returns:
            dict[str, Any]: Combined dictionary of component variables from control block parents
        """
        # TODO:
        # Address comment in get_control_block_immediate_parent_variables()

        control_component_vars: dict[str, Any] = {}
        parent_vars_list: list[dict[str, Any]] = []
        current_parent = self.parent
        max_depth = 100  # Safety limit to prevent infinite loops
        depth = 0

        # First collect all parent variables in order
        while current_parent and current_parent.control_block_type is not None:
            parent_vars_list.append(current_parent.component_variables)
            current_parent = current_parent.parent

            depth += 1
            if depth >= max_depth:
                self.logger.warning(
                    f"Reached maximum depth ({max_depth}) while traversing parent chain. "
                    "Possible circular reference detected."
                )
                break

        # Then apply them in reverse order (furthest ancestor first, closest parent last)
        for parent_vars in reversed(parent_vars_list):
            control_component_vars.update(parent_vars)

        return control_component_vars

    def get_context_variables_hierarchical(self) -> dict:
        """
        Recursively gets iteration_variables/ condition_variables through the execution context hierarchy.

        This method first looks in the current execution context for the specified variable,
        and then searches through parent contexts recursively.

        """
        variables = {}

        # INFO: Execution results should be handled with $hier{}
        # variable = {**self.execution_results}

        if self.control_block_type == ControlBlockTypeEnum.foreach:
            variables.update(self.iteration_variables)
        # elif self.control_block_type == ControlBlockTypeEnum.conditional:
        #    variables.update(self.condition_variables)
        else:
            pass

        # If not found, check parent contexts recursively
        if self.parent:
            _pvars = self.parent.get_context_variables_hierarchical()
            variables.update(_pvars)

        return variables


ContextT = TypeVar("ContextT", bound=ExecutionContext)
