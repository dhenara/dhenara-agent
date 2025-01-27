from typing import Any

import requests


class Client:
    def __init__(self, api_key: str, environment: str = "production"):
        self.api_key = api_key
        self.environment = environment

    async def execute_flow(self, flow_config: dict, input_data: dict):
        pass


class DhenaraClient:
    def __init__(self, api_key: str, base_url: str = "https://api.dhenara.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> dict[Any, Any]:
        headers = {"Authorization": f"ApiKey {self.api_key}", "Content-Type": "application/json"}

        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def create_client_token(self, domain: str) -> dict[str, str]:
        return self._make_request("POST", "/api/v1/client-tokens", json={"domain": domain})
