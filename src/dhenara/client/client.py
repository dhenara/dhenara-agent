from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, Union

import httpx

from dhenara.client import ClientConfig, DhenaraAPIError, DhenaraConnectionError, UrlSettings
from dhenara.types import DhenRunEndpoint
from dhenara.types.base import pydantic_endpoint


class Client:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.dhenara.com",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.config = ClientConfig(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            max_retries=max_retries,
        )

        self._sync_client = httpx.Client(
            timeout=timeout,
            headers=self._get_headers(),
        )
        self._async_client = httpx.AsyncClient(
            timeout=timeout,
            headers=self._get_headers(),
        )
        self.url_setting = UrlSettings(base_url=base_url)

        self._customer_id = None
        self._workspace_id = None
        self._endpoint_id = None
        self._credentials_token = None

    # def get_jwt_token(self):
    #    response = requests.get(f"{self.base_url}/get-jwt-token", headers={"Authorization": self.api_key})
    #    response.raise_for_status()
    #    self.token = self.get_jwt_token()
    #    return response.json()["token"]

    def _set_credentials(self, customer_id: str, workspace_id: str, endpoint_id, credentials_token):
        self._customer_id = customer_id
        self._workspace_id = workspace_id
        self._endpoint_id = endpoint_id
        self._credentials_token = credentials_token

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"ApiKey {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "dhenara-python-sdk/1.0",
        }

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle API response and raise appropriate exceptions"""
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = {}
            try:
                error_detail = response.json()
            except:
                error_detail = {"detail": response.text}

            raise DhenaraAPIError(
                f"API request failed: {e!s}",
                status_code=response.status_code,
                response=error_detail,
            )
        except httpx.RequestError as e:
            raise DhenaraConnectionError(f"Connection error: {e!s}")

    def create_client_token(self, domain: str) -> dict[str, str]:
        """Create a client token for the specified domain"""
        response = self._sync_client.post(
            f"{self.config.base_url}/api/v1/client-tokens",
            json={"domain": domain},
        )
        return self._handle_response(response)

    # def create_dhenrun_ep(
    #    self,
    #    workspace_id: str,
    #    name: str,
    #    definition: dict,
    #    action: str,
    #    flow_data: FlowDefinition,
    #    description: str = "",
    # ) -> dict[str, Any]:
    #    """Define a new flow in the specified workspace"""
    #    url = self.url_setting.get_full_url("devtime_dhenrun_ep")

    #    response = self._sync_client.post(
    #        url,
    #        json={
    #            "name": name,
    #            "definition": definition,
    #            "description": description,
    #        },
    #    )
    #    return self._handle_response(response)

    @pydantic_endpoint(DhenRunEndpoint)
    def create_endpoint(
        self,
        model_instance: DhenRunEndpoint,
    ) -> DhenRunEndpoint:
        """
        Create a new DhenRun endpoint.

        The method signature is automatically generated from DhenRunEndpoint model.
        """
        payload = model_instance.model_dump()

        url = self.url_setting.get_full_url("devtime_dhenrun_ep")
        response = self._sync_client.post(url=url, json=payload)
        result = self._handle_response(response)
        return DhenRunEndpoint(**result)

    # def create_endpoint(
    #    self,
    #    workspace_id: str,
    #    run_endpoint: DhenRunEndpoint | None = None,
    #    **kwargs,
    # ) -> dict[str, Any]:
    #    if run_endpoint is not None:
    #        payload = run_endpoint.dict(exclude_unset=True)
    #    else:
    #        try:
    #            run_endpoint = DhenRunEndpoint(**kwargs)
    #            payload = run_endpoint.dict(exclude_unset=True)
    #        except ValidationError as ve:
    #            raise ValueError(f"Invalid DhenRunEndpoint data: {ve}") from ve

    #    url = f"{self.base_url}/workspaces/{workspace_id}/dhenrun_endpoints/"

    #    response = self._sync_client.post(url, json=payload)

    #    if response.status_code == 201:
    #        return response.json()
    #    else:
    #        response.raise_for_status()

    def execute_flow(
        self,
        flow_id: str,
        input_data: Any,
        stream: bool = False,
    ) -> Union[dict[str, Any], AsyncGenerator[bytes, None]]:
        """Execute a flow synchronously"""

        url = self.url_setting.get_full_url("runtime_dhenrun_ep")
        if stream:
            raise ValueError("Streaming is only supported in async mode")

        response = self._sync_client.post(
            url,
            json={"input": input_data},
        )
        return self._handle_response(response)

    async def execute_flow_async(
        self,
        flow_id: str,
        input_data: Any,
        stream: bool = False,
    ) -> Union[dict[str, Any], AsyncIterator[bytes]]:
        """
        Execute a flow asynchronously.

        Args:
            flow_id: The ID of the flow to execute
            input_data: The input data for the flow
            stream: Whether to stream the response

        Returns:
            Either a dictionary with the response or an async iterator of bytes for streaming
        """

        if not stream:
            response = await self._async_client.post(
                f"{self.config.base_url}/api/flows/{flow_id}/execute/",
                json={"input": input_data},
            )
            return self._handle_response(response)

        # If streaming is requested, use async generator
        async def stream_response() -> AsyncGenerator[bytes, None]:
            async with self._async_client.stream(
                "POST",
                f"{self.config.base_url}/api/flows/{flow_id}/execute/",
                json={"input": input_data},
            ) as response:
                if response.status_code != 200:
                    raise DhenaraAPIError(
                        "Stream request failed",
                        status_code=response.status_code,
                        response={"detail": await response.aread()},
                    )
                async for chunk in response.aiter_bytes():
                    yield chunk

        return stream_response()

    def get_flow_status(self, execution_id: str) -> dict[str, Any]:
        """Get the status of a flow execution"""
        response = self._sync_client.get(
            f"{self.config.base_url}/api/executions/{execution_id}/status/",
        )
        return self._handle_response(response)

    async def get_flow_status_async(self, execution_id: str) -> dict[str, Any]:
        """Get the status of a flow execution asynchronously"""
        response = await self._async_client.get(
            f"{self.config.base_url}/api/executions/{execution_id}/status/",
        )
        return self._handle_response(response)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._sync_client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._async_client.aclose()
