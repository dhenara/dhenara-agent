from dhenara.types import BaseModel


class ClientConfig(BaseModel):
    api_key: str
    base_url: str = "https://api.dhenara.com"
    timeout: int = 30
    max_retries: int = 3
