from typing import Any, TypeVar

from pydantic import Field

from dhenara.agent.types.base import BaseModel


class CallbackInput(BaseModel):
    final_args: dict[str, Any] = Field(
        default_factory=dict,
        description="Final Arguments used in the callback",
    )


class CallbackOutputData(BaseModel):
    callable_result: dict | None = Field(
        ...,
        description="Result returned by callback",
    )


class CallbackOutput(BaseModel):
    data: CallbackOutputData


class CallbackOutcome(BaseModel):
    callable_result: dict | None


CallbackInputT = TypeVar("CallbackInputT", bound=CallbackInput)
CallbackOutputT = TypeVar("CallbackOutputT", bound=CallbackOutput)
CallbackOutcomeT = TypeVar("CallbackOutcomeT", bound=CallbackOutcome)
