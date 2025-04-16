from abc import ABC, abstractmethod
from typing import Any, TypeVar

from dhenara.agent.dsl.base import ExecutionContext

from .enums import ExecutableTypeEnum


# INFO: Not a Pydantic Class as the the `ExecutableBlock` cannot a Pydantic class
class Executable(ABC):
    """A generic executable element in the DSL."""

    @property
    @abstractmethod
    def executable_type(self) -> ExecutableTypeEnum:
        pass

    # TODO_FUTURE:
    # system_instructions:list[str] # Useful for flow-block/agent-node type

    @abstractmethod
    async def execute(self, context: "ExecutionContext") -> Any:
        """Execute the element in the given context."""
        pass


ExecutableT = TypeVar("ExecutableT", bound=Executable)
