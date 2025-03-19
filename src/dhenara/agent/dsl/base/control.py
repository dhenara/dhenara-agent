from typing import Any

from dhenara.agent.dsl.base import ExecutableBlock, ExecutableElement, ExecutionContext


class Conditional(ExecutableElement):
    def __init__(
        self,
        condition: str,
        then_branch: ExecutableElement | list[ExecutableElement],
        else_branch: ExecutableElement | list[ExecutableElement] | None = None,
    ):
        self.condition = condition
        self.then_branch = self._ensure_block(then_branch)
        self.else_branch = self._ensure_block(else_branch) if else_branch else None

    async def execute(self, context: "ExecutionContext") -> Any:
        condition_result = context.evaluate(self.condition)
        if condition_result:
            return await self.then_branch.execute(context)
        elif self.else_branch:
            return await self.else_branch.execute(context)
        return None

    def _ensure_block(self, element_or_elements: ExecutableElement | list[ExecutableElement]):
        if isinstance(element_or_elements, list):
            return ExecutableBlock(element_or_elements)
        return ExecutableBlock([element_or_elements])


class ForEach(ExecutableElement):
    def __init__(
        self,
        items: str,
        body: ExecutableElement | list[ExecutableElement],
        item_var: str = "item",
        index_var: str = "index",
        collect_results: bool = True,
        max_iterations: int | None = None,
    ):
        self.items = items
        self.body = self._ensure_block(body)
        self.item_var = item_var
        self.index_var = index_var
        self.collect_results = collect_results
        self.max_iterations = max_iterations

    async def execute(self, context: "ExecutionContext") -> list[Any]:
        """Execute the body for each item in the collection."""
        items = context.evaluate(self.items)
        results = []

        # Safety check
        if self.max_iterations and len(items) > self.max_iterations:
            items = items[: self.max_iterations]
            context.logger.warning(f"Limiting loop to {self.max_iterations} iterations")

        # Create a loop context for each iteration
        for i, item in enumerate(items):
            # Create a new context for this iteration
            loop_context = context.create_iteration_context({self.item_var: item, self.index_var: i})

            # Execute the body
            result = await self.body.execute(loop_context)

            # Merge iteration context back to parent
            context.merge_iteration_context(loop_context)

            # Collect results if needed
            if self.collect_results:
                results.append(result)

            # Record iteration outcome if configured
            await context.record_iteration_outcome(self, i, item, result)

        return results if self.collect_results else None

    def _ensure_block(self, elements: ExecutableElement | list[ExecutableElement]) -> ExecutableBlock:
        """Ensure the elements are wrapped in a Block."""
        if isinstance(elements, ExecutableBlock):
            return elements
        elif isinstance(elements, list):
            return ExecutableBlock(elements)
        else:
            return ExecutableBlock([elements])
