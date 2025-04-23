from typing import Any, Generic

from pydantic import Field

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentDefT,
    ContextT,
    NodeID,
)
from dhenara.agent.dsl.base.data.dad_template_engine import DADTemplateEngine
from dhenara.agent.run import RunContext
from dhenara.agent.types.base import BaseModel
from dhenara.ai.types.genai.dhenara.request.data import ObjectTemplate


class Conditional(BaseModel, Generic[ComponentDefT]):
    """Conditional branch construct."""

    statement: ObjectTemplate | None = Field(
        default=None,
        description=("Template to evaluvate from previous node results. This should resolve to a boolean."),
    )
    then_branch: ComponentDefinition = Field(..., description="Block to execute if condition is true")
    else_branch: ComponentDefinition | None = Field(default=None, description="Block to execute if condition is false")

    async def execute(
        self,
        component_id: NodeID,
        execution_context: ContextT,
        run_context: RunContext | None = None,
    ) -> Any:
        """Execute the appropriate branch based on the condition."""
        # Evaluate the condition
        condition_result = execution_context.evaluate_expression(self.statement)

        execution_context.logger.info(
            f"Conditional {component_id}: Statement '{self.statement}' evaluated to {condition_result}"
        )

        # Create branch-specific IDs
        # then_id = f"{component_id}_then"
        # else_id = f"{component_id}_else"
        then_id = "then"
        else_id = "else"

        condition_variables = {
            "evaluation_result": condition_result,
            "statement": self.statement,
        }
        # Create a new context for the branch with the evaluation result
        branch_context = execution_context.__class__(
            component_id=then_id if condition_result else else_id,
            component_definition=self.then_branch if condition_result else self.else_branch,
            run_context=execution_context.run_context,
            parent=execution_context,
            condition_variables=condition_variables,
        )

        # Execute the appropriate branch
        if condition_result:
            if self.then_branch:
                return await self.then_branch.execute(
                    component_id=then_id,
                    execution_context=branch_context,
                    run_context=run_context,
                )
            return None
        elif self.else_branch:
            return await self.else_branch.execute(
                component_id=else_id,
                execution_context=branch_context,
                run_context=run_context,
            )
        return None


class ForEach(BaseModel, Generic[ComponentDefT]):
    """Loop construct that executes a block for each item in a collection."""

    statement: ObjectTemplate | None = Field(
        default=None,
        description=("Template to evaluvate from previous node results. This should resolve to an iterable."),
    )
    item_var: str = Field(default="item", description="Variable name for current item")
    index_var: str = Field(default="index", description="Variable name for current index")
    body: ComponentDefT = Field(..., description="Block to execute for each item")
    collect_results: bool = Field(default=True, description="Whether to collect results")
    max_iterations: int | None = Field(default=None, description="Maximum iterations")

    async def execute(
        self,
        component_id: NodeID,
        execution_context: ContextT,
        run_context: RunContext | None = None,
    ) -> Any:
        """Execute the body for each item in the collection."""
        # Evaluate the statement expression to get the iterable

        _rendered = DADTemplateEngine.render_dad_template(
            template=self.statement,
            variables={},
            execution_context=execution_context,
        )
        items = _rendered

        if not items:
            execution_context.logger.error(f"ForEach statement '{self.statement}' evaluated to empty or None")
            return []

        results = []

        # Apply iteration limit if configured
        if self.max_iterations and len(items) > self.max_iterations:
            execution_context.logger.warning(f"Limiting loop to {self.max_iterations} iterations")
            items = items[: self.max_iterations]

        # Execute for each item
        for i, item in enumerate(items):
            # Create a new ID for this iteration's execution
            # iteration_id = f"{component_id}_iter_{i}"
            iteration_id = f"iter_{i}"

            # Create iteration-specific context with the current item and index
            iteration_variables = {
                self.item_var: item,
                self.index_var: i,
            }

            # Create a new execution context for this iteration
            iteration_context = execution_context.__class__(
                component_id=iteration_id,
                component_definition=self.body,
                run_context=execution_context.run_context,
                parent=execution_context,
                iteration_variables=iteration_variables,
            )

            # Execute the body with this context
            result = await self.body.execute(
                component_id=iteration_id,
                execution_context=iteration_context,
                run_context=run_context,
            )

            # Collect results if configured
            if self.collect_results:
                results.append(result)

        return results if self.collect_results else None
