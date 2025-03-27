from datetime import datetime
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import Field

from dhenara.agent.dsl.base import ComponentDefinition, ExecutableBlock, ExecutableElement, ExecutionContext
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseModel
from dhenara.ai.types.resource import ResourceConfig

ElementT = TypeVar("ElementT", bound=ExecutableElement)
BlockT = TypeVar("BlockT", bound=ExecutableBlock)
ContextT = TypeVar("ContextT", bound=ExecutionContext)
ComponentDefT = TypeVar("ComponentDefT", bound=ComponentDefinition)


class ComponentExecutor(BaseModel, Generic[ElementT, BlockT, ContextT, ComponentDefT]):
    """Executor for Flow definitions."""

    definition: ComponentDefT = Field(...)

    # Concrete classes to use
    context_class: ClassVar[type[ContextT]]
    block_class: ClassVar[type[BlockT]]

    run_context: RunContext

    async def execute(
        self,
        resource_config: ResourceConfig = None,
    ) -> dict[str, Any]:
        """Execute a flow with the given initial data."""
        # Create the execution context

        execution_context = self.context_class(
            # flow_definition=flow_definition,
            resource_config=resource_config,
            created_at=datetime.now(),
            run_context=self.run_context,
            run_env_params=self.run_context.run_env_params,  # TODO: Remove
            artifact_manager=self.run_context.artifact_manager,
        )

        # Execute the flow
        block = self.block_class(self.definition.elements)
        await block.execute(
            execution_context=execution_context,
        )
        return execution_context.results
