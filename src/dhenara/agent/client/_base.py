import logging
from collections.abc import AsyncIterator, Iterator
from types import TracebackType
from typing import Any, TypeVar

import httpx
from typing_extensions import Self  # for Python <3.11

from dhenara.agent.client import UrlSettings
from dhenara.agent.config import get_config
from dhenara.agent.types.base import BaseModel
from dhenara.ai.types.shared.api import (
    ApiRequest,
    ApiRequestActionTypeEnum,
    ApiResponse,
    ApiResponseMessageStatusCode,
    ApiResponseStatus,
    SSEResponse,
)
from dhenara.ai.types.shared.platform import DhenaraAPIError, DhenaraConnectionError

from ._stream import StreamProcessor

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class ClientConfig(BaseModel):
    api_key: str
    ep_version: str | None = "v1"
    base_url: str = "https://api.dhenara.com"
    timeout: int = 30
    max_retries: int = 3


class _ClientBase:
    """
    Dhenara API client for making API requests.

    Supports both synchronous and asynchronous operations with proper resource management.
    """

    def __init__(
        self,
        version: str,
        api_key: str,
        base_url: str,
        ep_version: str | None,
        timeout: int,
        max_retries: int,
    ) -> None:
        """Initialize the API client."""
        self.__version__ = version or "1.0.1"

        # Get values from configuration if not provided
        self.config = get_config()

        if not self.config:
            raise ValueError("Failed to load config")

        _api_key = api_key or self.config.api_keys.get("dhenara")
        _base_url = base_url or self.config.client_config.endpoints.get("dhenara", "https://api.dhenara.com")
        _ep_version = ep_version or self.config.client_config.ep_version

        self._client_config = ClientConfig(
            api_key=_api_key,
            ep_version=_ep_version,
            base_url=_base_url.rstrip("/"),
            max_retries=max_retries,
        )

        self._sync_client = httpx.Client(
            timeout=timeout,
            headers=self._get_headers(),
            follow_redirects=True,
        )
        self._async_client = httpx.AsyncClient(
            timeout=timeout,
            headers=self._get_headers(),
            follow_redirects=True,
        )
        self._url_settings = UrlSettings(
            base_url=base_url,
            ep_version=ep_version,
        )

    def _get_headers(self) -> dict[str, str]:
        """Get the headers for API requests."""
        return {
            # "Authorization": f"Bearer {self._client_config.api_key}",
            "X-Api-Key": self._client_config.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "dhenara-python-sdk/1.0",
        }

    def _parse_response(
        self,
        response_data: dict[str, Any],
        model_class: type[T] | None = None,
    ) -> ApiResponse[T]:
        """Parse raw response data into a typed ApiResponse object.

        This function handles the conversion of raw API response data into a structured
        ApiResponse object, optionally validating the data payload against a specified
        Pydantic model.

        Args:
            response_data: Raw response dictionary from the API
            model_class: Optional Pydantic model class for data payload validation

        Returns:
            ApiResponse[T]: Parsed and validated API response object

        Raises:
            DhenaraAPIError: If response parsing or validation fails

        Example:
            ```python
            response_data = {"status": "success", "data": {"id": 1, "name": "test"}, "messages": []}
            result = _parse_response(response_data, UserModel)
            ```
        """
        try:
            status_str = response_data.get("status", None)
            status = ApiResponseStatus(status_str) if status_str else None
            if status in [ApiResponseStatus.SUCCESS, ApiResponseStatus.PENDING]:
                if response_data.get("data") and model_class:
                    parsed_data = model_class.model_validate(response_data["data"])
                    response_data["data"] = parsed_data
                return ApiResponse[T].model_validate(response_data)
            elif status in [ApiResponseStatus.ERROR, ApiResponseStatus.FAIL]:
                return ApiResponse.model_validate(response_data)
            else:
                raise DhenaraAPIError(
                    message=f"Invalid response data: {response_data}",
                    status_code=ApiResponseMessageStatusCode.FAIL_SERVER_ERROR,
                    response=response_data,
                )

        except ValueError as e:
            raise DhenaraAPIError(
                message=f"Failed to parse API response: {e}",
                status_code=ApiResponseMessageStatusCode.FAIL_SERVER_ERROR,
                response=response_data,
            )

    def _make_request(
        self,
        model_instance: BaseModel,
        action: ApiRequestActionTypeEnum,
        endpoint: str,
        response_model: type[T],
    ) -> ApiResponse[T]:
        """
        Make a request to the API with proper model validation.

        Args:
            model_instance: The request data model
            action: The API action to perform
            endpoint: The API endpoint
            response_model: The expected response model

        Returns:
            Validated API response
        """
        api_request = ApiRequest[type(model_instance)](
            data=model_instance.model_dump(),
            action=action,
        )

        url = self._url_settings.get_full_url(endpoint)
        response = self._sync_client.post(
            url=url,
            json=api_request.model_dump(),
        )
        return self._handle_response(response, response_model)

    async def _make_request_async(
        self,
        model_instance: BaseModel,
        action: ApiRequestActionTypeEnum,
        endpoint: str,
        response_model: type[T],
    ) -> ApiResponse[T]:
        """Async version of _make_request."""
        api_request = ApiRequest[type(model_instance)](
            data=model_instance.model_dump(),
            action=action,
        )

        url = self._url_settings.get_full_url(endpoint)
        response = await self._async_client.post(
            url=url,
            json=api_request.model_dump(),
        )
        return self._handle_response(response, response_model)

    def _handle_response(
        self,
        response: httpx.Response,
        model_class: type[T] | None = None,
    ) -> ApiResponse[T]:
        """Handle API response and raise appropriate exceptions."""
        try:
            response.raise_for_status()
            parsed_response = self._parse_response(response.json(), model_class)
            error_msg = parsed_response.check_for_status_errors()
            if error_msg:
                logger.error(error_msg)
            return parsed_response
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

    def _prepare_streaming_headers(self) -> dict[str, str]:
        """Prepare headers for streaming requests."""
        headers = self._get_headers()
        headers["Accept"] = "text/event-stream"
        return headers

    def _make_streaming_request(
        self,
        model_instance: BaseModel,
        action: ApiRequestActionTypeEnum,
        endpoint: str,
        response_model: type[T],
    ) -> Iterator[SSEResponse]:
        """Make a synchronous streaming request."""
        api_request = ApiRequest[type(model_instance)](
            data=model_instance.model_dump(),
            action=action,
        )

        url = self._url_settings.get_full_url(endpoint)
        with self._sync_client.stream(
            "POST",
            url=url,
            json=api_request.model_dump(),
            headers=self._prepare_streaming_headers(),
        ) as response:
            response.raise_for_status()
            yield from StreamProcessor.handle_sync_stream(response=response, response_model=response_model)

    async def _make_streaming_request_async(
        self,
        model_instance: BaseModel,
        action: ApiRequestActionTypeEnum,
        endpoint: str,
        response_model: type[T],
    ) -> AsyncIterator[SSEResponse]:
        """Make an asynchronous streaming request."""
        api_request = ApiRequest[type(model_instance)](
            data=model_instance.model_dump(),
            action=action,
        )

        url = self._url_settings.get_full_url(endpoint)
        async with self._async_client.stream(
            "POST",
            url=url,
            json=api_request.model_dump(),
            headers=self._prepare_streaming_headers(),
        ) as response:
            response.raise_for_status()
            async for chunk in StreamProcessor.handle_async_stream(response=response, response_model=response_model):
                yield chunk

    # Context manager support
    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._sync_client.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._async_client.aclose()
