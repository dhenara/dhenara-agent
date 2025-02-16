from dhenara.types.base import BaseModel


class AIModelCallConfig(BaseModel):
    """Configuration for AI model calls"""

    max_tokens: int | None = None
    streaming: bool = False
    options: dict = None
    metadata: dict = None
    timeout: float | None = None
    retries: int = 3
    retry_delay: float = 1.0
    max_retry_delay: float = 10.0
    test_mode: bool = False

    def get_user(self):
        user = self.metadata.get("user", None)
        if not user:
            user = self.metadata.get("user_id", None)

        return user
