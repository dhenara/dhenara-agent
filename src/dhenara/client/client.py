import json
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, Union

import httpx

from dhenara.client import ClientConfig, DhenaraAPIError, DhenaraConnectionError, UrlSettings
from dhenara.types import DhenRunEndpoint
from dhenara.types.api import ApiResponse, ApiResponseMessageStatusCode
from dhenara.types.base import BaseModel, pydantic_endpoint
from dhenara.types.flow import FlowExecutionResult


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

    # def get_jwt_token(self):
    #    response = requests.get(f"{self.base_url}/get-jwt-token", headers={"Authorization": self.api_key})
    #    response.raise_for_status()
    #    self.token = self.get_jwt_token()
    #    return response.json()["token"]

    # def _set_credentials(self, customer_id: str, workspace_id: str, endpoint_id, credentials_token):
    #     self._customer_id = customer_id
    #     self._workspace_id = workspace_id
    #     self._endpoint_id = endpoint_id
    #     self._credentials_token = credentials_token

    def _get_headers(self) -> dict[str, str]:
        return {
            # "Authorization": f"Bearer {self.config.api_key}",
            "X-Api-Key": f"{self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "dhenara-python-sdk/1.0",
        }

    def _parse_response(
        self,
        response_data: dict,
        model_class: type[BaseModel] | None = None,
    ) -> ApiResponse:
        """Parse raw response into ApiResponse object"""
        try:
            # If model_class is provided, parse the data field with it
            if response_data.get("data") and model_class:
                parsed_data = model_class(**response_data["data"])
                response_data["data"] = parsed_data

            return ApiResponse(**response_data)
        except ValueError as e:
            raise DhenaraAPIError(
                message=f"Failed to parse API response: {e}",
                status_code=ApiResponseMessageStatusCode.FAIL_SERVER_ERROR,
                response=response_data,
            )

    def _handle_response(
        self,
        response: httpx.Response,
        model_class: type[BaseModel] | None = None,
    ) -> ApiResponse:
        """Handle API response and raise appropriate exceptions"""
        try:
            response.raise_for_status()
            response_data = response.json()
            return self._parse_response(response_data, model_class)
        except httpx.HTTPStatusError as e:
            error_detail = {}
            try:
                error_detail = response.json()
            except:
                error_detail = {"detail": response.text}

            raise DhenaraAPIError(
                message=f"API request failed: {e}",
                status_code=ApiResponseMessageStatusCode.FAIL_SERVER_ERROR,
                response=error_detail,
            )
        except httpx.RequestError as e:
            raise DhenaraConnectionError(f"Connection error: {e}")

    @pydantic_endpoint(DhenRunEndpoint)
    def create_endpoint(
        self,
        model_instance: DhenRunEndpoint,
    ) -> ApiResponse[DhenRunEndpoint]:
        """Create a new DhenRun endpoint."""
        payload = model_instance.model_dump()
        payload["action"] = "create"
        url = self.url_setting.get_full_url("devtime_dhenrun_ep")
        response = self._sync_client.post(url=url, json=payload)
        return self._handle_response(response, DhenRunEndpoint)

    def execute_flow(
        self,
        flow_id: str,
        input_data: Any,
        stream: bool = False,
    ) -> Union[ApiResponse[FlowExecutionResult], AsyncGenerator[bytes, None]]:
        """Execute a flow synchronously"""

        url = self.url_setting.get_full_url("runtime_dhenrun_ep")
        if stream:
            raise ValueError("Streaming is only supported in async mode")

        response = self._sync_client.post(
            url,
            json={"input": input_data},
        )
        return self._handle_response(response, FlowExecutionResult)

    async def execute_flow_async(
        self,
        flow_id: str,
        input_data: Any,
        stream: bool = False,
    ) -> Union[ApiResponse[FlowExecutionResult], AsyncIterator[bytes]]:
        """
        Execute a flow asynchronously.

        Args:
            flow_id: The ID of the flow to execute
            input_data: The input data for the flow
            stream: Whether to stream the response

        Returns:
            Either an ApiResponse with FlowExecutionResult or an async iterator of bytes for streaming
        """
        if not stream:
            response = await self._async_client.post(
                f"{self.config.base_url}/api/flows/{flow_id}/execute/",
                json={"input": input_data},
            )
            return self._handle_response(response, FlowExecutionResult)

        async def stream_response() -> AsyncGenerator[bytes, None]:
            async with self._async_client.stream(
                "POST",
                f"{self.config.base_url}/api/flows/{flow_id}/execute/",
                json={"input": input_data},
            ) as response:
                if response.status_code != 200:
                    error_detail = await response.aread()
                    try:
                        error_json = json.loads(error_detail)
                    except:
                        error_json = {"detail": error_detail.decode("utf-8")}

                    raise DhenaraAPIError(
                        message="Stream request failed",
                        status_code=ApiResponseMessageStatusCode.FAIL_SERVER_ERROR,
                        response=error_json,
                    )
                async for chunk in response.aiter_bytes():
                    yield chunk

        return stream_response()

    def get_flow_status(self, execution_id: str) -> ApiResponse[FlowExecutionResult]:
        """
        Get the status of a flow execution

        Args:
            execution_id: The ID of the flow execution to check

        Returns:
            ApiResponse containing the FlowExecutionResult
        """
        response = self._sync_client.get(
            f"{self.config.base_url}/api/executions/{execution_id}/status/",
        )
        return self._handle_response(response, FlowExecutionResult)

    async def get_flow_status_async(
        self,
        execution_id: str,
    ) -> ApiResponse[FlowExecutionResult]:
        """
        Get the status of a flow execution asynchronously

        Args:
            execution_id: The ID of the flow execution to check

        Returns:
            ApiResponse containing the FlowExecutionResult
        """
        response = await self._async_client.get(
            f"{self.config.base_url}/api/executions/{execution_id}/status/",
        )
        return self._handle_response(response, FlowExecutionResult)

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any | None) -> None:
        self._sync_client.close()

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any | None,
    ) -> None:
        await self._async_client.aclose()
