from collections.abc import AsyncIterator, Iterator
from typing import Any, TypeVar

from dhenara.agent.dsl.base import NodeID, NodeInput
from dhenara.agent.types.fns import pydantic_endpoint
from dhenara.agent.types.functional_types import (
    DhenRunEndpointReq,
    DhenRunEndpointRes,
    ExecuteDhenRunEndpointReq,
    ExecuteDhenRunEndpointRes,
)
from dhenara.ai.types.shared.api import (
    ApiRequest,
    ApiRequestActionTypeEnum,
    ApiResponse,
    BaseModel,
    DhenaraAPIError,
    SSEResponse,
)

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
        timeout: int = 300,
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

    @pydantic_endpoint(DhenRunEndpointReq)
    def create_endpoint(
        self,
        model_instance: DhenRunEndpointReq,
    ) -> ApiResponse[DhenRunEndpointRes]:
        """Create a new DhenRun endpoint."""
        data = model_instance.model_dump()
        api_request = ApiRequest[DhenRunEndpointReq](
            data=data,
            action=ApiRequestActionTypeEnum.create,
        )
        payload = api_request.model_dump()

        url = self._url_settings.get_full_url("devtime_dhenrun_ep")
        response = self._sync_client.post(url=url, json=payload)
        return self._handle_response(response, DhenRunEndpointRes)

    def execute_endpoint(
        self,
        refnum: str,
        initial_inputs: dict[NodeID, NodeInput],
        stream: bool = False,
        response_model: type[T] = ExecuteDhenRunEndpointRes,
    ) -> ApiResponse[ExecuteDhenRunEndpointRes] | Iterator[SSEResponse]:
        """Execute an endpoint synchronously."""

        request_data = ExecuteDhenRunEndpointReq(
            refnum=refnum,
            initial_inputs=initial_inputs,
        )

        if stream:
            return self._make_streaming_request(
                model_instance=request_data,
                action=ApiRequestActionTypeEnum.run,
                endpoint="runtime_dhenrun_ep",
                response_model=response_model,
            )

        return self._make_request(
            model_instance=request_data,
            action=ApiRequestActionTypeEnum.run,
            endpoint="runtime_dhenrun_ep",
            response_model=response_model,
        )

    async def execute_endpoint_async(
        self,
        refnum: str,
        node_input: NodeInput | dict,
        stream: bool = False,
        response_model: type[T] = ExecuteDhenRunEndpointRes,
    ) -> ApiResponse[ExecuteDhenRunEndpointRes] | AsyncIterator[dict]:
        """Execute an endpoint asynchronously."""
        input_data = node_input.model_dump() if isinstance(node_input, BaseModel) else node_input
        request_data = ExecuteDhenRunEndpointReq(
            refnum=refnum,
            input=input_data,
        )

        if stream:
            return self._make_streaming_request_async(
                model_instance=request_data,
                action=ApiRequestActionTypeEnum.run,
                endpoint="runtime_dhenrun_ep",
                response_model=response_model,
            )

        return await self._make_request_async(
            model_instance=request_data,
            action=ApiRequestActionTypeEnum.run,
            endpoint="runtime_dhenrun_ep",
            response_model=response_model,
        )

    async def _handle_response_async(
        self,
        response: Any,
        response_model: type[T],
    ) -> ApiResponse[T]:
        """Handle async API response and convert to appropriate type."""
        if response.status_code != 200:
            error_data = await response.json()
            raise DhenaraAPIError(
                f"Request failed with status {response.status_code}",
                status_code=response.status_code,
                error_data=error_data,
            )

        response_data = await response.json()
        return ApiResponse[T].model_validate(response_data)

    # TODO
    def get_endpoint_status(self, execution_id: str) -> ApiResponse[ExecuteDhenRunEndpointRes]:
        """
        Get the status of a endpoint execution

        Args:
            execution_id: The ID of the endpoint execution to check

        Returns:
            ApiResponse containing the ExecuteDhenRunEndpointRes
        """
        response = self._sync_client.get(
            f"{self.config.base_url}/api/executions/{execution_id}/status/",
        )
        return self._handle_response(response, ExecuteDhenRunEndpointRes)

    # TODO
    async def get_endpoint_status_async(
        self,
        execution_id: str,
    ) -> ApiResponse[ExecuteDhenRunEndpointRes]:
        """
        Get the status of a endpoint execution asynchronously

        Args:
            execution_id: The ID of the endpoint execution to check

        Returns:
            ApiResponse containing the ExecuteDhenRunEndpointRes
        """
        response = await self._async_client.get(
            f"{self.config.base_url}/api/executions/{execution_id}/status/",
        )
        return self._handle_response(response, ExecuteDhenRunEndpointRes)
