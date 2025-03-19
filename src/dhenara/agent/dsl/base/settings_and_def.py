from abc import abstractmethod
from typing import Any, Generic, TypeVar

from dhenara.agent.dsl.base import ExecutionContext
from dhenara.agent.types.base import BaseModel, BaseModelABC


class ExecutableNodeOutcomeSettings(BaseModel):
    """Settings for recording node outcomes."""

    enabled: bool = True
    path_template: str = "{node_id}"
    filename_template: str = "{node_id}.json"
    content_template: str | None = None
    commit: bool = True
    commit_message_template: str | None = None


ContextT = TypeVar("ContextT", bound=ExecutionContext)


class ExecutableNodeDefinition(BaseModelABC, Generic[ContextT]):  # Abstract Class
    """Base class for all node definitions."""

    outcome_settings: ExecutableNodeOutcomeSettings | None = None

    class Config:
        arbitrary_types_allowed = True  # TODO: Review

    @abstractmethod
    async def execute(self, context: ContextT) -> Any:
        """Execute this node definition."""
        pass
