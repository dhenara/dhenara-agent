from abc import abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import Field

from dhenara.agent.dsl.base import (
    ExecutionContext,
    NodeGitSettings,
    NodeID,
    NodeInput,
    NodeRecordSettings,
    NodeSettings,
)
from dhenara.agent.dsl.events import EventType
from dhenara.agent.types.base import BaseModelABC
from dhenara.ai.types.resource import ResourceConfigItem

ContextT = TypeVar("ContextT", bound=ExecutionContext)


class ExecutableNodeDefinition(BaseModelABC, Generic[ContextT]):  # Abstract Class
    """Base class for all node definitions."""

    node_type: str

    pre_events: list[EventType | str] = Field(
        default_factory=list,
        description="Event need to be triggered before node execution.",
    )
    post_events: list[EventType | str] = Field(
        default_factory=list,
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

    git_settings: NodeGitSettings | None = Field(
        default=None,
        description="Node Git Settings.",
    )

    streaming: bool = False  # TODO: Remove

    @property
    def pre_execute_input_required(self):
        return EventType.node_input_required in self.pre_events

    # @abstractmethod
    async def execute(
        self,
        node_id: NodeID,
        execution_context: ContextT,
        # resource_config: ResourceConfig,
    ) -> Any:
        # self.resource_config = resource_config

        execution_context.set_current_node(node_id)
        # initial_input= execution_context.get_initial_inputs()

        node_executor = self.get_node_executor()

        # Execute non-streaming node
        result = await node_executor.execute(
            node_id=node_id,
            node_definition=self,
            execution_context=execution_context,
        )
        return result

    @abstractmethod
    def get_node_executor(self):  # NodeExecutor:
        """Get the node_executor for this node definition."""
        pass

    # -------------------------------------------------------------------------
    async def load_from_previous_run(
        self,
        node_id: NodeID,
        execution_context: ContextT,
    ) -> Any:
        executer = self.get_node_executor()
        result_class = executer.get_result_class()

        result_data = await execution_context.run_context.load_node_from_previous_run(
            node_id=node_id,
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
        if not self.resources:
            return False

        return any(existing_resource.is_same_as(resource) for existing_resource in self.resources)
