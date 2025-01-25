# schemas.py
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ComponentConfig(BaseModel):
    type: str
    config: Dict[str, Any]
    order: int
    is_parallel: bool = False

    @validator("type")
    def validate_type(cls, v):
        allowed_types = {"AIModel", "RAG", "Streaming"}
        if v not in allowed_types:
            raise ValueError(f"Component type must be one of {allowed_types}")
        return v


class FlowDefinitionSchema(BaseModel):
    id: Optional[uuid.UUID]
    name: str
    description: Optional[str]
    components: List[ComponentConfig]
    is_active: bool = True
    is_test_mode: bool = False


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
