from typing import Any, Generic, TypeVar

from pydantic import Field, field_validator

from dhenara.agent.dsl.base import ComponentDefT, Conditional, ContextT, Executable, ForEach, NodeID
from dhenara.agent.run.run_context import RunContext
from dhenara.agent.types.base import BaseModel


# A generic node that could later be specialized
class ExecutableComponent(Executable, BaseModel, Generic[ComponentDefT, ContextT]):
    id: NodeID = Field(
        ...,
        description="Unique human readable identifier for the node",
        min_length=1,
        max_length=150,
        pattern="^[a-zA-Z0-9_]+$",
    )

    definition: ComponentDefT | ForEach | Conditional = Field(...)

    @field_validator("id")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate node identifier format.
        Raises ValueError if identifier is empty or contains only whitespace
        """
        if not v.strip():
            raise ValueError("FlowNode identifier cannot be empty or whitespace")
        return v

    async def execute(
        self,
        execution_context: ContextT | None = None,
        run_context: RunContext | None = None,
    ) -> Any:
        result = await self.definition.execute(
            component_id=self.id,
            execution_context=execution_context,
            run_context=run_context,
        )

        return result

    async def load_from_previous_run(self, execution_context: ContextT) -> Any:
        execution_context.logger.info(f"Loading previous run data for component {self.id} ")

        result = await self.definition.load_from_previous_run(
            component_id=self.id,
            execution_context=execution_context,
        )
        return result


ComponentT = TypeVar("ComponentDeT", bound=ExecutableComponent)
