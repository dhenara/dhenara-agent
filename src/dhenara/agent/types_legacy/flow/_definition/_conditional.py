from typing import ClassVar

from pydantic import Field, model_validator

from dhenara.agent.types.flow import BaseFlow, FlowTypeEnum


class ConditionalFlow(BaseFlow):
    """Flow that executes based on a condition."""

    flow_type: ClassVar[FlowTypeEnum | None] = FlowTypeEnum.condition

    condition_expr: str = Field(
        ...,
        description="Expression to evaluate for the condition (Python expression)",
    )

    true_branch: BaseFlow = Field(
        ...,
        description="Flow to execute if condition is true",
    )

    false_branch: BaseFlow | None = Field(
        default=None,
        description="Flow to execute if condition is false (optional)",
    )

    context_vars: list[str] = Field(
        default_factory=list,
        description="List of variables from execution context needed for evaluation",
    )

    # eval_context: list[str] = Field(
    #    default_factory=list,
    #    description="List of node outputs to include in the evaluation context",
    # )

    @model_validator(mode="after")
    def validate_branches(self) -> "ConditionalFlow":
        """Validate that branches are proper flow definitions."""
        if not isinstance(self.true_branch, BaseFlow):
            raise ValueError("true_branch must be a flow definition")

        if self.false_branch is not None and not isinstance(self.false_branch, BaseFlow):
            raise ValueError("false_branch must be a flow definition")

        return self
