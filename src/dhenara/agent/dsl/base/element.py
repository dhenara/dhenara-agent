from abc import abstractmethod
from typing import Any

from dhenara.agent.dsl.base import ExecutionContext
from dhenara.agent.types.base import BaseModelABC


# class BaseElement(BaseModelABC):
class ExecutableElement(BaseModelABC):
    """A generic executable element in the DSL."""

    @abstractmethod
    async def execute(self, context: "ExecutionContext") -> Any:
        """Execute the element in the given context."""
        pass
