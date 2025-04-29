# stream_processor.py
from collections.abc import AsyncIterator, Iterator
from typing import TypeVar

import httpx

from dhenara.agent.types.base import BaseModel
from dhenara.ai.types.shared.api import (
    SSEErrorCode,
    SSEErrorData,
    SSEErrorResponse,
    SSEEventType,
    SSEResponse,
)

T = TypeVar("T", bound=BaseModel)


class StreamProcessor:
    """Helper class to process streaming responses."""

    @staticmethod
    def decode_line(line: str | bytes) -> str:
        """Decode line from bytes if needed"""
        if isinstance(line, bytes):
            return line.decode("utf-8")
        return line

    @staticmethod
    def parse_sse_event(
        event_str: str,
        response_model: type[T],
    ) -> SSEResponse | None:
        """Parse SSE event using the SSEResponse parser"""
        if not event_str.strip():
            return None

        try:
            parsed = SSEResponse.parse_sse(event_str, response_model)

            if parsed.event == SSEEventType.TOKEN_STREAM:
                return parsed

            elif parsed.event == SSEEventType.ERROR:
                return parsed
            else:
                SSEErrorResponse(
                    data=SSEErrorData(
                        error_code=SSEErrorCode.client_decode_error,
                        message=f"Unknonw event {parsed.event}",
                    ),
                )

            return parsed

        except Exception as e:
            return SSEErrorResponse(
                data=SSEErrorData(
                    error_code=SSEErrorCode.client_decode_error,
                    message=f"Failed to parse SSE event: {e}",
                ),
            )

    @staticmethod
    def handle_sync_stream(
        response: httpx.Response,
        response_model: type[T],
    ) -> Iterator[SSEResponse]:
        """Handle synchronous streaming response."""
        buffer = []

        for line in response.iter_lines():
            line = StreamProcessor.decode_line(line)

            if not line.strip():
                # Empty line indicates end of event
                if buffer:
                    event = StreamProcessor.parse_sse_event("\n".join(buffer), response_model)
                    if event:
                        yield event
                    buffer = []
                continue

            buffer.append(line)

        # Handle any remaining data in buffer
        if buffer:
            event = StreamProcessor.parse_sse_event("\n".join(buffer), response_model)
            if event:
                yield event

    @staticmethod
    async def handle_async_stream(
        response,
        response_model: type[T],
    ) -> AsyncIterator[SSEResponse]:
        """Handle asynchronous streaming response."""
        buffer = []

        async for line in response.aiter_lines():
            line = StreamProcessor.decode_line(line)

            if not line.strip():
                # Empty line indicates end of event
                if buffer:
                    event = StreamProcessor.parse_sse_event("\n".join(buffer), response_model)
                    if event:
                        yield event
                    buffer = []
                continue

            buffer.append(line)

        # Handle any remaining data in buffer
        if buffer:
            event = StreamProcessor.parse_sse_event("\n".join(buffer), response_model)
            if event:
                yield event
