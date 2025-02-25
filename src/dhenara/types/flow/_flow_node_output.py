# Copyright 2024-2025 Dhenara Inc. All rights reserved.

from typing import Any

from dhenara_ai.types.shared.base import BaseEnum, BaseModel
from pydantic import Field, field_validator


class ResponseProtocolEnum(BaseEnum):
    """Enumeration of available response protocols for node outputs."""

    HTTP = "http"  # One-time request/response
    HTTP_SSE = "http_sse"  # Server pushes events, client only receives. Eg: Streaming and Push-notification
    WEBSOCKET = "websocket"  # Full-duplex, bi-directional
    GRPC = "grpc"  # Bi-directional streaming, high performance
    MQTT = "mqtt"  # Pub/sub messaging, IoT focused


class ResponseContentEnum(BaseEnum):
    """Types of content that can be included in a response."""

    FULL = "full"  # Complete node output
    STATUS = "status"  # Only status updates
    METADATA = "metadata"  # Only metadata
    SUMMARY = "summary"  # Summarized output
    ERROR = "error"  # Error messages only
    CUSTOM = "custom"  # Custom filtered content


class ResponseFilterConfig(BaseModel):
    """Configuration for filtering response content."""

    content_type: ResponseContentEnum = Field(
        default=ResponseContentEnum.FULL,
        description="Type of content to include in the response",
    )
    include_fields: list[str] | None = Field(
        default=None,
        description="Specific fields to include in the response (if content_type is CUSTOM)",
    )
    exclude_fields: list[str] | None = Field(
        default=None,
        description="Fields to exclude from the response",
    )
    max_length: int | None = Field(
        default=None,
        description="Maximum length of the response content",
    )

    @field_validator("include_fields", "exclude_fields")
    @classmethod
    def validate_field_lists(cls, v):
        if v is not None and not v:  # Check if list is empty
            return None
        return v

    @field_validator("include_fields")
    @classmethod
    def validate_custom_content_fields(cls, v, values):
        if values.get("content_type") == ResponseContentEnum.CUSTOM and not v:
            raise ValueError("include_fields must be specified when content_type is CUSTOM")
        return v


class NodeResponseSettings(BaseModel):
    """Configuration for node response handling."""

    enabled: bool = Field(
        default=True,
        description="Whether to send response for this node",
    )
    protocol: ResponseProtocolEnum = Field(
        default=ResponseProtocolEnum.HTTP,
        description="Protocol to use for sending the response",
    )
    response_filters: list[ResponseFilterConfig] = Field(
        default_factory=lambda: [ResponseFilterConfig(content_type=ResponseContentEnum.FULL)],
        description="List of content filters to apply to the response",
    )
    streaming_chunk_size: int | None = Field(
        default=None,
        description="Size of chunks for streaming responses (if applicable)",
    )
    retry_config: dict[str, Any] | None = Field(
        default=None,
        description="Configuration for response delivery retries",
    )
    custom_headers: dict[str, str] | None = Field(
        default=None,
        description="Custom headers to include in the response",
    )

    @field_validator("streaming_chunk_size")
    @classmethod
    def validate_streaming_chunk_size(cls, v, values):
        if v is not None and values.get("protocol") not in [
            ResponseProtocolEnum.HTTP_STREAM,
            ResponseProtocolEnum.SSE,
        ]:
            raise ValueError("streaming_chunk_size is only applicable for streaming protocols")
        return v

    @field_validator("retry_config")
    @classmethod
    def validate_retry_config(cls, v):
        if v is not None:
            required_keys = {"max_attempts", "retry_delay"}
            if not all(key in v for key in required_keys):
                raise ValueError(f"retry_config must contain all of these keys: {required_keys}")
        return v
