# dhenara/agent/engine/executor.py
from typing import Any, Generic, TypeVar

from pydantic import Field

from dhenara.agent.dsl.base import ComponentDefinition, ExecutableBlock, ExecutableElement, ExecutionContext
from dhenara.agent.types.base import BaseModel
from dhenara.agent.utils.io.artifact_manager import ArtifactManager

ElementT = TypeVar("ElementT", bound=ExecutableElement)
BlockT = TypeVar("BlockT", bound=ExecutableBlock)
ContextT = TypeVar("ContextT", bound=ExecutionContext)
ComponentDefT = TypeVar("ComponentDefT", bound=ComponentDefinition)


class ComponentExecutor(BaseModel, Generic[ElementT, BlockT, ContextT, ComponentDefT]):
    """Executor for Flow definitions."""

    definition: ComponentDefT = Field(...)
    artifact_manager: ArtifactManager | None = Field(default=None)

    async def execute(
        self,
        initial_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a flow with the given initial data."""
        # Create the execution context
        context = ContextT(
            initial_data=initial_data,
            artifact_manager=self.artifact_manager,
        )

        # Execute the flow
        block = BlockT(self.definition.elements)
        await block.execute(context)
        return context.results
