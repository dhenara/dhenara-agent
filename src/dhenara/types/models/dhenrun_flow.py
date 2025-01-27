from enum import Enum
from typing import Any, Optional

from pydantic import Field, field_validator

from ..base import BaseModel


class FlowExecutionModeEnum(str, Enum):
    """Enum defining flow execution modes.

    Attributes:
        sequential: Components execute one after another
        parallel: Components execute simultaneously
    """

    sequential = "sequential"
    parallel = "parallel"


class FlowExecutionTypeEnum(str, Enum):
    """Enum defining types of flow execution components.

    Attributes:
        ai_model_call: AI model inference call
        rag_create: RAG index creation
        rag_retrieve: RAG retrieval operation
        streaming: Streaming operation
    """

    ai_model_call = "ai_model_call"
    rag_create = "rag_create"
    rag_retrieve = "rag_retrieve"
    streaming = "streaming"


class FlowComponent(BaseModel):
    """Model representing a flow component.

    A flow component defines a single operational unit within a flow with its
    execution parameters and configuration.

    Attributes:
        type: Type of flow execution component
        mode: Execution mode for sub-components
        order: Execution order in the flow
        config: Component specific configuration
    """

    type: FlowExecutionTypeEnum = Field(
        ...,
        description="Type of flow execution component",
        examples=["ai_model_call", "rag_create"],
    )
    mode: FlowExecutionModeEnum = Field(
        ...,
        description="Execution mode for sub-components, if any",
        examples=["sequential"],
    )
    order: int = Field(
        ...,
        description="Execution order",
        ge=0,
        examples=[1],
    )
    config: dict[str, Any] = Field(
        ...,
        description="Component specific configuration parameters",
        examples=[{"model_name": "gpt-4", "temperature": 0.7}],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "ai_model_call",
                    "mode": "sequential",
                    "order": 1,
                    "config": {
                        "model_name": "gpt-4",
                        "temperature": 0.7,
                    },
                }
            ]
        }
    }


class FlowDefinition(BaseModel):
    """Model representing a complete flow definition.

    A flow definition contains metadata about the flow and its components.

    Attributes:
        name: Name of the flow
        description: Optional description of the flow's purpose
        components: List of flow components
        is_active: Whether the flow is currently active
    """

    name: str = Field(
        ...,
        description="Name of the flow",
        min_length=1,
        max_length=255,
        examples=["Document Processing Flow"],
    )
    description: Optional[str] = Field(
        None,
        description="Optional description of the flow's purpose",
        examples=["Flow for processing and analyzing documents"],
    )
    components: list[FlowComponent] = Field(
        ...,
        description="List of flow components in execution order",
        min_items=1,
    )
    is_active: bool = Field(
        True,  # noqa: FBT003
        description="Whether the flow is currently active",
    )

    @field_validator("components")
    @classmethod
    def validate_component_order(cls, v: list[FlowComponent]) -> list[FlowComponent]:
        """Validate that component orders are unique and sequential."""
        orders = [c.order for c in v]
        if len(orders) != len(set(orders)):
            raise ValueError("Component orders must be unique")
        if sorted(orders) != list(range(min(orders), max(orders) + 1)):
            raise ValueError("Component orders must be sequential")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Document Processing Flow",
                    "description": "Flow for processing and analyzing documents",
                    "components": [
                        {
                            "type": "rag_create",
                            "mode": "sequential",
                            "order": 0,
                            "config": {"index_name": "docs"},
                        },
                        {
                            "type": "ai_model_call",
                            "mode": "sequential",
                            "order": 1,
                            "config": {"model_name": "gpt-4"},
                        },
                    ],
                    "is_active": True,
                }
            ]
        }
    }


"""
class FlowContext(BaseModel):
    flow_id: uuid.UUID
    user_input: str
    workspace_id: str
    metadata: Optional[Dict[str, Any]]
    intermediate_results: Dict[str, Any] = Field(default_factory=dict)


class FlowResponse(BaseModel):
    execution_id: uuid.UUID
    status: str
    result: Optional[Any]
    error: Optional[str]


class FlowExecution(BaseModel):
    input: str = Field(..., max_length=1000, description="User input for the AI model.")
    # Add other fields as necessary

    @field_validator("input")
    @classmethod
    def sanitize_input(cls, v: str) -> str:
        ## Example sanitization: remove script tags
        # sanitized = re.sub(r"<script.*?>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)

        sanitized = v
        if len(sanitized) > 1000:
            raise ValueError("Input exceeds maximum allowed length.")
        return sanitized

"""
