from datetime import datetime

from pydantic import Field, model_validator

from dhenara.agent.dsl.agent.agent_node import AgentNode
from dhenara.agent.types.base import BaseModel
from dhenara.ai.types.shared.platform import PlatformEnvTypeEnum


# -----------------------------------------------------------------------------
class DhenRunEndpointBase(BaseModel):
    """
    Base model for Run Endpoint with common fields.

    This model contains fields that are common between create/update operations
    and the stored database model.
    """

    name: str = Field(
        ...,
        description="Endpoint name for identification",
        min_length=5,
        max_length=200,
        examples=["my-production-endpoint"],
    )

    description: str | None = Field(
        None,
        description="Optional description of the endpoint's purpose",
        examples=["Endpoint for processing customer data"],
    )

    allowed_domains: list[str] | None = Field(
        default=None,
        description="List of domains allowed to access this endpoint",
        examples=[["example.com", "api.example.com"]],
    )

    is_active: bool = Field(
        default=True,
        description="Flag indicating if the endpoint is currently active",
    )


# -----------------------------------------------------------------------------
class DhenRunEndpointReq(DhenRunEndpointBase):
    """
    Model for creating a new Run Endpoint.

    This model is used when creating a new endpoint and includes either
    a agent_id reference or the complete agent data.
    """

    id: str | None = Field(
        default=None,
        description="Unique identifier for the endpoint",
    )

    reference_number: str | None = Field(
        default=None,
        description="Unique reference_number for the endpoint",
    )

    agent_id: str | None = Field(
        default=None,
        description="Reference ID of an existing Agent",
        examples=["agent_12345"],
    )

    agent: AgentNode | None = Field(
        default=None,
        description="Complete Agent data when creating a new agent with the endpoint",
    )

    @model_validator(mode="after")
    def validate_agent_references(self) -> "DhenRunEndpointReq":
        """Validate that either agent or agent_id is provided, but not both."""
        if self.agent and self.agent_id:
            raise ValueError("Cannot specify both 'agent' and 'agent_id'")
        if not (self.agent or self.agent_id):
            raise ValueError("Must provide either 'agent' or 'agent_id'")
        return self


# -----------------------------------------------------------------------------
class DhenRunEndpointRes(DhenRunEndpointBase):
    """
    Complete Run Endpoint model representing stored data.

    This model extends the base model and includes all fields that are stored
    in the database, including system fields like ID and timestamps.
    """

    id: str = Field(
        ...,
        description="Unique identifier for the endpoint",
    )

    reference_number: str = Field(
        ...,
        description="Unique reference_number for the endpoint",
    )

    workspace_id: str = Field(
        ...,
        description="ID of the workspace this endpoint belongs to",
    )

    agent_id: str = Field(
        ...,
        description="Reference to the associated Agent",
    )

    env_type: PlatformEnvTypeEnum = Field(
        ...,
        description="Environment type for this endpoint",
    )

    created_at: datetime = Field(
        ...,
        description="Timestamp when the endpoint was created",
    )

    updated_at: datetime = Field(
        ...,
        description="Timestamp when the endpoint was last updated",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "production-endpoint",
                "description": "Main production endpoint",
                "workspace_id": "123e4567-e89b-12d3-a456-426614174001",
                "agent_id": "123e4567-e89b-12d3-a456-426614174002",
                "env_type": "production",
                "allowed_domains": ["api.example.com"],
                "is_active": True,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
            },
        }
