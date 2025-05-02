from typing import Any, Generic

from pydantic import Field

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentDefT,
    ContextT,
    ControlBlockTypeEnum,
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
    true_branch: ComponentDefinition = Field(..., description="Block to execute if condition is true")
    false_branch: ComponentDefinition | None = Field(default=None, description="Block to execute if condition is false")

    async def execute(
        self,
        component_id: NodeID,
        execution_context: ContextT,
        run_context: RunContext | None = None,
    ) -> Any:
        """Execute the appropriate branch based on the condition."""
        # Evaluate the condition
        result = None

        _rendered = DADTemplateEngine.render_dad_template(
            template=self.statement,
            variables={},
            execution_context=execution_context,
        )
        evaluation_result = _rendered

        execution_context.logger.info(
            f"Conditional {component_id}: Statement '{self.statement}' evaluated to {evaluation_result}"
        )

        if evaluation_result is None or isinstance(evaluation_result, str):
            execution_context.logger.error(
                f"Conditional statement '{self.statement}' evaluated to a type {type(evaluation_result)} "
                "not to a bool convertable type"
            )
            return result

        evaluation_result = bool(evaluation_result)

        # Create branch-specific IDs
        # true_id = f"{component_id}_is_true"
        # false_id = f"{component_id}_is_false"
        true_id = "is_true"
        false_id = "is_false"

        # INFO: No need to add `condition_variables` similar to iteration_variables like
        # condition_variables = {
        #     "evaluation_result": evaluation_result,
        #     "statement": self.statement,
        # }
        # as there won't be a need to access the `evaluation_result` which is always True/False.
        # The sub component seletion is based on the result unlike in an iteration scenario

        # Create a new context for the branch with the evaluation result

        # Execute the appropriate branch
        if evaluation_result:
            true_branch_context = execution_context.__class__(
                control_block_type=ControlBlockTypeEnum.conditional,
                component_id=true_id,
                component_definition=self.true_branch,
                run_context=execution_context.run_context,
                parent=execution_context,
            )

            result = await self.true_branch.execute(
                component_id=true_id,
                execution_context=true_branch_context,
                run_context=run_context,
            )
            return result
        elif self.false_branch:
            false_branch_context = execution_context.__class__(
                control_block_type=ControlBlockTypeEnum.conditional,
                component_id=false_id,
                component_definition=self.false_branch,
                run_context=execution_context.run_context,
                parent=execution_context,
            )

            result = await self.false_branch.execute(
                component_id=false_id,
                execution_context=false_branch_context,
                run_context=run_context,
            )
        return result


class ForEach(BaseModel, Generic[ComponentDefT]):
    """Loop construct that executes a block for each item in a collection."""

    statement: ObjectTemplate | None = Field(
        default=None,
        description=("Template to evaluvate from previous node results. This should resolve to an iterable."),
    )
    item_var: str = Field(default="item", description="Variable name for current item")
    index_var: str = Field(default="index", description="Variable name for current index")
    body: ComponentDefT = Field(..., description="Block to execute for each item")
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
        execution_context.logger.debug(
            f"ForEach {component_id}: Statement '{self.statement}' evaluated to a type {type(items)} with value {items}"
        )

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
                control_block_type=ControlBlockTypeEnum.foreach,
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

            results.append(result)

        return results
