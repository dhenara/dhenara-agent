from abc import ABC, abstractmethod
from typing import Any

from dhenara.agent.dsl.base import ExecutionContext

from .enums import ExecutableTypeEnum


# INFO: Not a Pydantic Class as the the `ExecutableBlock` cannot a Pydantic class
class Executable(ABC):
    """Base interface for all executable elements in the DSL."""

    @property
    @abstractmethod
    def executable_type(self) -> ExecutableTypeEnum:
        """Return the type of executable."""
        pass

    @abstractmethod
    async def execute(self, execution_context: ExecutionContext) -> Any:
        """Execute the element in the given context."""
        pass
