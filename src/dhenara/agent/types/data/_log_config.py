from typing import Literal

from pydantic import Field

from dhenara.agent.types.base import BaseModel

LogLevelType = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]


class LogConfig(BaseModel):
    """Configuration for logging levels across different modules."""

    loggers: dict[str, LogLevelType] = Field(
        default_factory=dict,
        description="List of logger configurations with their respective log levels",
        examples=[
            {"dhenara.agent": "INFO"},
            {"dhenara.agent.pro": "DEBUG"},
            {"dhenara.ai": "INFO"},
            {"dhenara.agent.pro.worker": "INFO"},
            {"dhenara.agent.pro.client": "INFO"},
            {"http": "WARNING"},
            {"websocket": "WARNING"},
        ],
    )
