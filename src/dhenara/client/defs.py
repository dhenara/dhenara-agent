from enum import Enum

from dhenara.types import BaseModel


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ClientConfig(BaseModel):
    api_key: str
    base_url: str = "https://api.dhenara.com"
    timeout: int = 30
    max_retries: int = 3
