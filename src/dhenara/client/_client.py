import json
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, TypeVar, Union

from dhenara.client import DhenaraAPIError
from dhenara.types.api import (
    ApiRequest,
    ApiRequestActionTypeEnum,
    ApiResponse,
    ApiResponseMessageStatusCode,
    DhenRunEndpoint,
    DhenRunEndpointCreate,
)
from dhenara.types.base import BaseModel, pydantic_endpoint
from dhenara.types.flow import FlowExecutionResult

from ._base import _ClientBase

T = TypeVar("T", bound=BaseModel)


class Client(_ClientBase):
    """
    Dhenara API client for making API requests.

    Supports both synchronous and asynchronous operations with proper resource management.
    """

    __version__ = "1.0.1"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.dhenara.com",
        timeout: int = 30,
        max_retries: int = 3,
        ep_version: str | None = "v1",
    ) -> None:
        super().__init__(
            api_key=api_key,
            version=self.__version__,
            ep_version=ep_version,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    @pydantic_endpoint(DhenRunEndpointCreate)
    def create_endpoint(
        self,
        model_instance: DhenRunEndpointCreate,
    ) -> ApiResponse[DhenRunEndpoint]:
        """Create a new DhenRun endpoint."""
        data = model_instance.model_dump()

        # Ensure the response data is JSON serializable
        api_request = ApiRequest[DhenRunEndpointCreate](
            data=data,
            action=ApiRequestActionTypeEnum.create,
        )
        payload = api_request.model_dump()

        url = self._url_settings.get_full_url("devtime_dhenrun_ep")
        response = self._sync_client.post(url=url, json=payload)
        return self._handle_response(response, DhenRunEndpoint)

    def execute_flow(
        self,
        flow_id: str,
        input_data: Any,
        stream: bool = False,
    ) -> Union[ApiResponse[FlowExecutionResult], AsyncGenerator[bytes, None]]:
        """Execute a flow synchronously"""

        url = self.url_settinurl_settinggs.get_full_url("runtime_dhenrun_ep")
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
