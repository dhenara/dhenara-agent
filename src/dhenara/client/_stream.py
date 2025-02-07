# _stream.py
import json
from collections.abc import AsyncIterator, Iterator
from typing import Union

import httpx

from dhenara.types.base import BaseEnum


class StreamEventType(BaseEnum):
    """Types of streaming events"""

    TOKEN = "token"
    ERROR = "error"
    DONE = "done"
    META = "meta"
    UNKNOWN = "unknown"


class StreamChunk:
    """Represents a processed stream chunk"""

    def __init__(
        self,
        event_type: StreamEventType = StreamEventType.TOKEN,
        data: dict | None = None,
        error: str | None = None,
    ):
        self.event_type = event_type
        self.data = data or {}
        self.error = error

    @property
    def is_error(self) -> bool:
        return self.event_type == StreamEventType.ERROR

    @property
    def is_done(self) -> bool:
        return self.event_type == StreamEventType.DONE

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "error": self.error,
        }


class StreamProcessor:
    """Helper class to process streaming responses."""

    @staticmethod
    def decode_line(line: Union[str, bytes]) -> str:
        """Decode line from bytes if needed"""
        if isinstance(line, bytes):
            return line.decode("utf-8")
        return line

    @staticmethod
    def parse_sse_line(line: str) -> tuple[str, str]:
        """Parse SSE line into field and value"""
        if ":" not in line:
            return line, ""

        field, value = line.split(":", 1)
        if value.startswith(" "):
            value = value[1:]
        return field, value

    @staticmethod
    def process_chunk(chunk: Union[str, bytes]) -> StreamChunk:
        """Process a single chunk of streaming data."""
        try:
            chunk = StreamProcessor.decode_line(chunk)

            # Handle empty lines
            if not chunk.strip():
                return None

            # Parse SSE fields
            field, value = StreamProcessor.parse_sse_line(chunk)

            # Handle different SSE fields
            if field == "event":
                try:
                    event_type = StreamEventType(value)
                except ValueError:
                    event_type = StreamEventType.UNKNOWN
                return StreamChunk(event_type=event_type)

            elif field == "data":
                try:
                    data = json.loads(value)
                    event_type = StreamEventType(data.get("event", "token"))

                    # Check for completion
                    if data.get("done", False):
                        event_type = StreamEventType.DONE

                    return StreamChunk(
                        event_type=event_type,
                        data=data,
                    )
                except json.JSONDecodeError as e:
                    return StreamChunk(
                        event_type=StreamEventType.ERROR,
                        error=f"Invalid JSON in stream: {e}",
                    )

            # Ignore other SSE fields (id, retry) for now
            return None

        except Exception as e:
            return StreamChunk(
                event_type=StreamEventType.ERROR,
                error=f"Stream processing error: {e}",
            )

    @staticmethod
    def handle_sync_stream(response: httpx.Response) -> Iterator[StreamChunk]:
        """Handle synchronous streaming response."""
        buffer = []

        for line in response.iter_lines():
            if not line:
                # Empty line indicates end of event
                if buffer:
                    chunk = StreamProcessor.process_chunk("\n".join(buffer))
                    if chunk:
                        yield chunk
                    buffer = []
                continue

            buffer.append(StreamProcessor.decode_line(line))

    @staticmethod
    async def handle_async_stream(response) -> AsyncIterator[StreamChunk]:
        """Handle asynchronous streaming response."""
        buffer = []

        async for line in response.aiter_lines():
            if not line:
                # Empty line indicates end of event
                if buffer:
                    chunk = StreamProcessor.process_chunk("\n".join(buffer))
                    if chunk:
                        yield chunk
                    buffer = []
                continue

            buffer.append(StreamProcessor.decode_line(line))
