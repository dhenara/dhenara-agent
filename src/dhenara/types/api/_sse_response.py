import json
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import Field

from dhenara.types.base import BaseEnum, BaseModel

# Type variable for generic data types
T = TypeVar("T", bound=BaseModel)


class SSEEventType(BaseEnum):
    """Types of Server-Sent Events"""

    TOKEN_STREAM = "token_stream"  # Streaming content chunks
    PUSH = "push"  # Push notifications
    ERROR = "error"  # Error events


class SSEDataChunk(BaseModel):
    """Base model for successful response data"""

    index: int = Field(
        default=0,
        description="Chunk index in the stream",
    )
    content: str = Field(
        ...,
        description="Chunk content",
    )
    done: bool = Field(
        default=False,
        description="Indicates if this is the final chunk",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional metadata for the event",
    )

    @property
    def is_done(self) -> bool:
        """Check if this is the final chunk"""
        return self.done


class SSEErrorCode(BaseEnum):
    server_error = "server_error"
    external_api_error = "external_api_error"


class SSEErrorData(BaseModel):
    """Model for error response data"""

    error_code: SSEErrorCode = Field(
        ...,
        description="Error code identifier",
    )
    message: str = Field(
        ...,
        description="Error message",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error details",
    )


class SSEResponse(BaseModel, Generic[T]):
    """Generic SSE response model supporting different data types"""

    event: SSEEventType = Field(
        ...,
        description="SSE Event type",
    )
    data: T = Field(
        ...,
        description="Event data payload",
    )
    id: str | None = Field(
        default=lambda: None,
        # default_factory=lambda: str(uuid4()),
        description="Unique event identifier",
    )
    retry: int | None = Field(
        default=None,
        description="Retry timeout in milliseconds",
    )

    class Config:
        arbitrary_types_allowed = True

    def set_random_id(self) -> str:
        self.id = str(uuid4())

    def is_error(self) -> bool:
        return self.event == SSEEventType.ERROR

    def to_sse_format(self) -> str:
        """Convert to SSE format string"""
        lines = []

        # Add event type
        lines.append(f"event: {self.event}")

        # Add ID
        lines.append(f"id: {self.id}")

        # Add retry if present
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        # Add data
        if isinstance(self.data, BaseModel):
            data_str = self.data.model_dump_json()
        elif isinstance(self.data, (dict, list)):
            data_str = json.dumps(self.data)
        else:
            data_str = str(self.data)

        # Handle multi-line data
        for line in data_str.splitlines():
            lines.append(f"data: {line}")

        return "\n".join(lines) + "\n\n"

    @classmethod
    def parse_sse(cls, sse_str: str) -> "SSEResponse[Any]":
        """Parse SSE format string into response object"""
        lines = sse_str.strip().split("\n")
        data = {}
        event = None
        event_id = None
        retry = None

        for line in lines:
            if not line:
                continue
            if ":" not in line:
                continue

            field, value = line.split(":", 1)
            value = value.lstrip()

            if field == "event":
                event = SSEEventType(value)
            elif field == "data":
                try:
                    data = json.loads(value)
                except json.JSONDecodeError:
                    data = value
            elif field == "id":
                event_id = value
            elif field == "retry":
                retry = int(value)

        return cls(
            event=event or SSEEventType.ERROR,
            data=data,
            id=event_id,
            retry=retry,
        )


class SSEErrorResponse(SSEResponse[SSEErrorData]):
    """Specialized SSE response for chat streaming"""

    event: SSEEventType = SSEEventType.ERROR
    data: SSEErrorData
