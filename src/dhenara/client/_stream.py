# stream_processor.py
from collections.abc import AsyncIterator, Iterator
from typing import Optional, Union

import httpx

from dhenara.types import (
    SSEErrorCode,
    SSEErrorData,
    SSEErrorResponse,
    SSEResponse,
)


class StreamProcessor:
    """Helper class to process streaming responses."""

    @staticmethod
    def decode_line(line: Union[str, bytes]) -> str:
        """Decode line from bytes if needed"""
        if isinstance(line, bytes):
            return line.decode("utf-8")
        return line

    @staticmethod
    def parse_sse_event(event_str: str) -> Optional[SSEResponse]:
        """Parse SSE event using the SSEResponse parser"""
        if not event_str.strip():
            return None

        try:
            return SSEResponse.parse_sse(event_str)
        except Exception as e:
            return SSEErrorResponse(
                data=SSEErrorData(
                    error_code=SSEErrorCode.server_error,
                    message=f"Failed to parse SSE event: {e}",
                ),
            )

    @staticmethod
    def handle_sync_stream(response: httpx.Response) -> Iterator[SSEResponse]:
        """Handle synchronous streaming response."""
        buffer = []

        for line in response.iter_lines():
            line = StreamProcessor.decode_line(line)

            if not line.strip():
                # Empty line indicates end of event
                if buffer:
                    event = StreamProcessor.parse_sse_event("\n".join(buffer))
                    if event:
                        yield event
                    buffer = []
                continue

            buffer.append(line)

        # Handle any remaining data in buffer
        if buffer:
            event = StreamProcessor.parse_sse_event("\n".join(buffer))
            if event:
                yield event

    @staticmethod
    async def handle_async_stream(response) -> AsyncIterator[SSEResponse]:
        """Handle asynchronous streaming response."""
        buffer = []

        async for line in response.aiter_lines():
            line = StreamProcessor.decode_line(line)

            if not line.strip():
                # Empty line indicates end of event
                if buffer:
                    event = StreamProcessor.parse_sse_event("\n".join(buffer))
                    if event:
                        yield event
                    buffer = []
                continue

            buffer.append(line)

        # Handle any remaining data in buffer
        if buffer:
            event = StreamProcessor.parse_sse_event("\n".join(buffer))
            if event:
                yield event
