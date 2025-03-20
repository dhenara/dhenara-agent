from abc import ABC

from dhenara.ai.types.shared.base import BaseEnum as DhenaraAIBaseEnum
from dhenara.ai.types.shared.base import BaseModel as DhenaraAIBaseModel


class BaseEnum(DhenaraAIBaseEnum):
    """Base class for all pydantic model definitions."""

    pass


class BaseModel(DhenaraAIBaseModel):
    """Base class for all pydantic model definitions."""

    pass


class BaseModelABC(BaseModel, ABC):
    """Base class for all pydantic model abstact definitions."""

    pass
