from typing import ClassVar

from pydantic import Field, model_validator

from dhenara.agent.types.flow import (
    BaseFlow,
    FlowTypeEnum,
)


class SwitchFlow(BaseFlow):
    """Flow that executes different branches based on an expression."""

    flow_type: ClassVar[FlowTypeEnum | None] = FlowTypeEnum.switch

    switch_expr: str = Field(
        ...,
        description="Expression to evaluate for switching",
    )

    cases: dict[str, BaseFlow] = Field(
        ...,
        description="Mapping of case values to flows to execute",
    )

    default: BaseFlow | None = Field(
        default=None,
        description="Default flow to execute if no case matches",
    )

    context_vars: list[str] = Field(
        default_factory=list,
        description="List of variables from execution context needed for evaluation",
    )

    @model_validator(mode="after")
    def validate_cases(self) -> "SwitchFlow":
        """Validate that cases are proper flow definitions."""
        for case_name, case_flow in self.cases.items():
            if not isinstance(case_flow, BaseFlow):
                raise ValueError(f"Case '{case_name}' must be a flow definition")

        if self.default is not None and not isinstance(self.default, BaseFlow):
            raise ValueError("default must be a flow definition")

        return self
