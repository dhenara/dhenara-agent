from asyncio import Event
from datetime import datetime
from typing import Any

from dhenara.types.base import BaseEnum, BaseModel
from dhenara.types.flow import FlowDefinition, FlowExecutionResults, FlowExecutionStatusEnum, FlowNodeExecutionResult, FlowNodeIdentifier, FlowNodeInput


class StreamingStatusEnum(BaseEnum):
    NOT_STARTED = "not_started"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"


class StreamingContext(BaseModel):
    status: StreamingStatusEnum = StreamingStatusEnum.NOT_STARTED
    completion_event: Event | None = None
    result: FlowNodeExecutionResult | None = None
    error: Exception | None = None

    @property
    def successfull(self) -> bool:
        return self.status == StreamingStatusEnum.COMPLETED


class FlowContext(BaseModel):
    endpoint_id: str
    flow_definition: FlowDefinition
    initial_input: FlowNodeInput
    execution_status: FlowExecutionStatusEnum = FlowExecutionStatusEnum.PENDING
    current_node_index: int = 0
    current_node_identifier: FlowNodeIdentifier | None = None
    execution_results: FlowExecutionResults[Any] = {}
    # final_output: FlowNodeOutput : Not reuired as it can be found from execution_results
    metadata: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    streaming_contexts: dict[FlowNodeIdentifier, StreamingContext | None] = {}

    def set_current_node(self, index: int):
        self.current_node_index = index
        self.current_node_identifier = self.flow_definition.nodes[index].identifier

    async def notify_streaming_complete(self, identifier: FlowNodeIdentifier, streaming_status: StreamingStatusEnum, result: FlowNodeExecutionResult) -> None:
        print(f"AJJJL identifier={identifier}, self.streaming_contexts={self.streaming_contexts}\n\nresult={result}")
        streaming_context = self.streaming_contexts[identifier]
        if not streaming_context:
            raise ValueError(f"notify_streaming_complete: Failed to get streaming_context for id {identifier}")

        streaming_context.status = streaming_status
        streaming_context.result = result
        self.execution_results[identifier] = result
        streaming_context.completion_event.set()
