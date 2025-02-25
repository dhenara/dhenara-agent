from dhenara_ai.types.shared.base import BaseModel


class ClientConfig(BaseModel):
    api_key: str
    version: str = "1.0.0"
    ep_version: str | None = "v1"
    base_url: str = "https://api.dhenara.com"
    timeout: int = 30
    max_retries: int = 3
