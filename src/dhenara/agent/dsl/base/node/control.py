from typing import Any

from dhenara.agent.dsl.base import ContextT, ExecutableBlock
from dhenara.agent.types.base import BaseModel


class Conditional(BaseModel):
    condition: str
    then_branch: ExecutableBlock
    else_branch: ExecutableBlock | None = None

    async def execute(self, execution_context: ContextT) -> list[Any]:
        condition_result = execution_context.evaluate(self.condition)
        conditional_context = execution_context.create_conditioanl_context({self.condition: condition_result})
        if condition_result:
            return await self.then_branch.execute(conditional_context)
        elif self.else_branch:
            return await self.else_branch.execute(conditional_context)
        return None


class ForEach(BaseModel):
    items: str
    body: ExecutableBlock
    item_var: str = "item"
    index_var: str = "index"
    collect_results: bool = True
    max_iterations: int | None = None

    async def execute(self, execution_context: ContextT) -> list[Any]:
        """Execute the body for each item in the collection."""
        items = execution_context.evaluate(self.items)
        results = []

        # Safety check
        if self.max_iterations and len(items) > self.max_iterations:
            items = items[: self.max_iterations]
            execution_context.logger.warning(f"Limiting loop to {self.max_iterations} iterations")

        # Create a loop context for each iteration
        for i, item in enumerate(items):
            # Create a new context for this iteration
            loop_context = execution_context.create_iteration_context({self.item_var: item, self.index_var: i})

            # Execute the body
            result = await self.body.execute(loop_context)

            # Merge iteration context back to parent
            execution_context.merge_iteration_context(loop_context)

            # Collect results if needed
            if self.collect_results:
                results.append(result)

            # Record iteration outcome if configured
            await execution_context.record_iteration_outcome(self, i, item, result)

        return results if self.collect_results else None
