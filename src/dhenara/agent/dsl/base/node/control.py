from typing import Any

from pydantic import Field

from dhenara.agent.dsl.base import ExecutionContext
from dhenara.agent.types.base import BaseModel

ExecutableBlock = Any  #  TODO:   Replace with component


class Conditional(BaseModel):
    """Conditional branch construct."""

    condition: str = Field(..., description="Expression that evaluates to boolean")
    then_branch: ExecutableBlock = Field(..., description="Block to execute if condition is true")
    else_branch: ExecutableBlock | None = Field(default=None, description="Block to execute if condition is false")

    async def execute(self, execution_context: ExecutionContext) -> Any:
        """Execute the appropriate branch based on the condition."""
        # Evaluate the condition
        condition_result = execution_context.evaluate_expression(self.condition)

        # Create a conditional context with the evaluation result
        conditional_context = execution_context.create_conditional_context({self.condition: condition_result})

        # Execute the appropriate branch
        if condition_result:
            return await self.then_branch.execute(conditional_context)
        elif self.else_branch:
            return await self.else_branch.execute(conditional_context)

        return None


class ForEach(BaseModel):
    """Loop construct that executes a block for each item in a collection."""

    items: str = Field(..., description="Expression that evaluates to an iterable")
    body: ExecutableBlock = Field(..., description="Block to execute for each item")
    item_var: str = Field(default="item", description="Variable name for current item")
    index_var: str = Field(default="index", description="Variable name for current index")
    collect_results: bool = Field(default=True, description="Whether to collect results")
    max_iterations: int | None = Field(default=None, description="Maximum iterations")

    async def execute(self, execution_context: ExecutionContext) -> list[Any]:
        """Execute the body for each item in the collection."""
        # Evaluate the items expression to get the iterable
        items = execution_context.evaluate_expression(self.items)
        if not items:
            execution_context.logger.warning(f"ForEach items '{self.items}' evaluated to empty or None")
            return []

        results = []

        # Apply iteration limit if configured
        if self.max_iterations and len(items) > self.max_iterations:
            execution_context.logger.warning(f"Limiting loop to {self.max_iterations} iterations")
            items = items[: self.max_iterations]

        # Execute for each item
        for i, item in enumerate(items):
            # Create iteration-specific context with the current item and index
            iteration_context = execution_context.create_iteration_context(
                {
                    self.item_var: item,
                    self.index_var: i,
                }
            )

            # Execute the body block with this context
            result = await self.body.execute(iteration_context)

            # Merge results back to parent context
            execution_context.merge_iteration_context(iteration_context)

            # Collect results if configured
            if self.collect_results:
                results.append(result)

            # Record iteration outcome if tracking is enabled
            await execution_context.record_iteration_outcome(self, i, item, result)

        return results if self.collect_results else None
