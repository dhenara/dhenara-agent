from typing import ClassVar, Literal

from pydantic import Field, model_validator

from dhenara.agent.types.flow import (
    BaseFlow,
    FlowTypeEnum,
)


class LoopFlow(BaseFlow):
    """Flow that executes in a loop."""

    flow_type: ClassVar[FlowTypeEnum | None] = FlowTypeEnum.loop

    loop_type: Literal["for", "while"] = Field(
        ...,
        description="Type of loop: 'for' (iterate over items) or 'while' (continue until condition is false)",
    )

    # For 'for' loops
    items_expr: str | None = Field(
        default=None,
        description="Expression that evaluates to an iterable (for 'for' loops)",
    )

    # For 'while' loops
    condition_expr: str | None = Field(
        default=None,
        description="Expression that evaluates to a boolean (for 'while' loops)",
    )

    body: BaseFlow = Field(
        ...,
        description="Flow to execute in each iteration",
    )

    max_iterations: int | None = Field(
        default=100,
        description="Maximum number of iterations (safety limit)",
    )

    context_vars: list[str] = Field(
        default_factory=list,
        description="List of variables from execution context needed for evaluation",
    )

    # Variables for iteration
    iteration_var: str = Field(
        default="iteration",
        description="Variable name for current iteration index",
    )

    item_var: str | None = Field(
        default="item",
        description="Variable name for current item (for 'for' loops)",
    )

    # State management
    capture_results: bool = Field(
        default=True,
        description="Whether to store results from each iteration",
    )

    pass_state: bool = Field(
        default=True,
        description="Whether to pass state between iterations",
    )

    @model_validator(mode="after")
    def validate_loop_settings(self) -> "LoopFlow":
        """Validate that loop settings are correct."""
        if self.loop_type == "for" and not self.items_expr:
            raise ValueError("items_expr must be provided for 'for' loops")

        if self.loop_type == "while" and not self.condition_expr:
            raise ValueError("condition_expr must be provided for 'while' loops")

        if not isinstance(self.body, BaseFlow):
            raise ValueError("body must be a flow definition")

        return self
