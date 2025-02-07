# _stream.py
import json
from collections.abc import AsyncIterator, Iterator

import httpx


class StreamProcessor:
    """Helper class to process streaming responses."""

    @staticmethod
    def process_chunk(chunk: bytes) -> dict:
        """Process a single chunk of streaming data."""
        if chunk.startswith("data: "):
            chunk = chunk[6:]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError as e:
                return {"status": "process_error", "message": f"Invalid JSON in stream. {e}"}
        # elif chunk.strip() == "[DONE]":
        #    return {"status": "done"}
        else:
            return {"status": "process_error", "message": "Invalid event stream encoding"}

    @staticmethod
    def handle_sync_stream(response: httpx.Response) -> Iterator[dict]:
        """Handle synchronous streaming response."""
        print(f"handle_sync_stream: response={response}\n\n")
        for line in response.iter_lines():
            if not line:
                continue
            yield StreamProcessor.process_chunk(line)

    @staticmethod
    # async def handle_async_stream(response: httpx.AsyncResponse) -> AsyncIterator[dict]:
    async def handle_async_stream(response) -> AsyncIterator[dict]:
        """Handle asynchronous streaming response."""
        async for line in response.aiter_lines():
            if not line:
                continue
            yield StreamProcessor.process_chunk(line)
