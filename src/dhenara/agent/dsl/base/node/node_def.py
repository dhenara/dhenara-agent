from abc import abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import Field

from dhenara.agent.dsl.base import (
    ContextT,
    ExecutableTypeEnum,
    NodeID,
    NodeInput,
    NodeRecordSettings,
    NodeSettings,
)
from dhenara.agent.dsl.events import EventType
from dhenara.agent.types.base import BaseModelABC
from dhenara.ai.types.resource import ResourceConfigItem

node_executor_registry = None


class ExecutableNodeDefinition(BaseModelABC, Generic[ContextT]):  # Abstract Class
    """
    Base class for node definitions. This ties together the node type,
    settings, and a lookup for the appropriate executor.
    """

    node_type: str
    executable_type: ExecutableTypeEnum

    pre_events: list[EventType | str] | None = Field(
        default=None,
        description="Event need to be triggered before node execution.",
    )
    post_events: list[EventType | str] | None = Field(
        default_factory=lambda: [EventType.node_execution_completed],
        description="Event need to be triggered after node execution.",
    )

    settings: NodeSettings | None = Field(
        default=None,
        description="Node Settings.",
    )
    record_settings: NodeRecordSettings | None = Field(
        default_factory=NodeRecordSettings,
        description="Record settings. Do not override if not sure what you are doing.",
    )

    streaming: bool = False  # TODO_FUTURE: Rename and implement SSE responses

    @property
    def trigger_pre_execute_input_required(self):
        return self.pre_events and EventType.node_input_required in self.pre_events

    @property
    def trigger_execution_completed(self):
        return self.post_events and EventType.node_execution_completed in self.post_events

    # @abstractmethod
    async def execute(
        self,
        node_id: NodeID,
        execution_context: ContextT,
    ) -> Any:
        # NOTE: set_current_node() will be done in the component executer as its where it decides should_execute,
        # which as depenency with current_node_identifier
        # execution_context.set_current_node(node_id)

        node_executor = self.get_node_executor()

        # Execute non-streaming node
        result = await node_executor.execute(
            node_id=node_id,
            node_definition=self,
            execution_context=execution_context,
        )
        return result

    def get_node_executor(self):
        """Get the node_executor for this node definition. This internally handles executor registry"""
        global node_executor_registry

        if node_executor_registry is None:
            from ._executor_registry import NodeExecutorRegistry

            node_executor_registry = NodeExecutorRegistry()

        executor = node_executor_registry.get_executor(
            executable_type=self.executable_type,
            node_type=self.node_type,
        )

        if executor is None:
            executor = node_executor_registry.register(
                executable_type=self.executable_type,
                node_type=self.node_type,
                executor_class=self.get_executor_class(),
            )

        return executor

    @abstractmethod
    def get_executor_class(self):
        """Get the node_executor class for this node definition."""
        pass

    # -------------------------------------------------------------------------
    async def load_from_previous_run(
        self,
        node_id: NodeID,
        execution_context: ContextT,
    ) -> Any:
        # NOTE: set_current_node() will be done in the component executer
        # execution_context.set_current_node(node_id)

        executer = self.get_node_executor()
        result_class = executer.get_result_class()

        result_data = await execution_context.load_from_previous_run(
            copy_artifacts=True,
        )

        if result_data:
            try:
                result = result_class(**result_data)
                # Set the result in the execution context
                execution_context.set_result(node_id, result)

                # TODO_FUTURE: record for tracing ?
                return result
            except Exception as e:
                execution_context.logger.error(f"Failed to load previous run data for node {node_id}: {e}")
                return None
        else:
            execution_context.logger.error(
                f"Falied to load data from previous execution result artifacts for node {node_id}"
            )
            return None

    # -------------------------------------------------------------------------
    def select_settings(
        self,
        node_input: NodeInput,
    ) -> NodeSettings:
        _settings = node_input.settings_override if node_input and node_input.settings_override else self.settings
        return _settings

    def is_streaming(self):
        return self.streaming

    def check_resource_in_node(self, resource: ResourceConfigItem) -> bool:
        """
        Checks if a given resource exists in the node's resource list.

        Args:
            resource: ResourceConfigItem object to check for

        Returns:
            bool: True if the resource exists in the node's resources, False otherwise
        """
        _resources = self.settings.resources or []

        return any(existing_resource.is_same_as(resource) for existing_resource in _resources)


NodeDefT = TypeVar("NodeDefT", bound=ExecutableNodeDefinition)
