from typing import Any, TypeVar

from pydantic import Field

from dhenara.agent.types.base import BaseModel


class ComponentInput(BaseModel):
    component_variables: dict[
        str,
        int | float | str | bool | list[Any] | dict[str, Any] | None,
    ] = Field(default_factory=dict)


ComponentInputT = TypeVar("ComponentInputT", bound=ComponentInput)
