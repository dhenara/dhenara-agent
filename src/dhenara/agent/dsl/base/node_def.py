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
from dhenara.agent.types.base import BaseModelABC
from dhenara.ai.types.resource import ResourceConfigItem

ContextT = TypeVar("ContextT", bound=ExecutionContext)


class ExecutableNodeDefinition(BaseModelABC, Generic[ContextT]):  # Abstract Class
    """Base class for all node definitions."""

    node_settings: NodeSettings | None = Field(
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

    # class Config:
    #    arbitrary_types_allowed = True  # TODO: Review

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
            node_definition=self,  # TODO: Change type in node_executor
            execution_context=execution_context,
            # initial_inputs=initial_inputs,
            # resource_config=execution_context.resource_config,
        )

        if result is not None:  # Streaming case will return an async generator
            return result

        execution_context.set_result(node_id, result)
        # TODO
        # if execution_context.execution_failed:
        #    execution_context.execution_status = ExecutionStatusEnum.FAILED
        #    return None

    @abstractmethod
    def get_node_executor(self):  # NodeExecutor:
        """Get the node_executor for this node definition."""
        pass

    # -------------------------------------------------------------------------
    def select_settings(
        self,
        node_id: str,
        node_input: NodeInput,
    ) -> NodeSettings:
        _settings = node_input.settings_override if node_input and node_input.settings_override else self.node_settings
        return _settings
        # TODO
        if node_input is None:
            raise ValueError(f"node_input is missing for node {node_id}")

        prompt = node_input.settings_override.prompt
        prompt_variables = node_input.variables or {}
        node_prompt = self.ai_settings.node_prompt if self.ai_settings and self.ai_settings.node_prompt else None
        input_content = node_input.content.get_content() if node_input and node_input.content else None

        if node_prompt:
            if input_content is None:
                input_content = ""  # NOTE: An empty string is better that the word None

            prompt_variables.update({"dh_input_content": input_content})

            return node_prompt.format(**prompt_variables)

        else:
            if not input_content:
                raise ValueError(f"Illegal Node setting for node {node_id}:  node_prompt and input_content are empty")

            return input_content

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
