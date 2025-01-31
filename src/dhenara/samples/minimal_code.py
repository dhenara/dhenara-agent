from enum import Enum

from pydantic import Field, model_validator

from dhenara.types.base import BaseModel

# TODO: Delete


class InternalDataObjectTypeEnum(str, Enum):
    conversation = "conversation"
    conversation_node = "conversation_node"
    conversation_space = "conversation_space"


class InternalDataObjParamsScopeEnum(str, Enum):
    current = "current"
    parent = "parent"


class InternalDataObjParams(BaseModel):
    object_type: InternalDataObjectTypeEnum
    object_id: str
    object_scope: InternalDataObjParamsScopeEnum

    @model_validator(mode="after")
    def validate_scope(self):
        if self.object_type == InternalDataObjectTypeEnum.conversation_node:
            if self.object_scope not in [InternalDataObjParamsScopeEnum.current, InternalDataObjParamsScopeEnum.parent]:
                raise ValueError("Invalid scope for conversation node")
        elif self.object_scope != InternalDataObjParamsScopeEnum.current:
            raise ValueError(f"{self.object_type} must have current scope")
        return self


class ResourceObjectTypeEnum(str, Enum):
    ai_model_endpoint = "ai_model_endpoint"
    rag_endpoint = "rag_endpoint"
    search_endpoint = "search_endpoint"


class Resource(BaseModel):
    object_type: ResourceObjectTypeEnum
    object_id: str | None = None
    query: dict | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.object_id and self.query:
            raise ValueError("Cannot have both object_id and query")
        return self


class FlowNodeInputActionEnum(str, Enum):
    generate_conversation_node = "generate_conversation_node"
    regenerate_conversation_node = "regenerate_conversation_node"
    delete_conversation_node = "delete_conversation_node"


class UserInput(BaseModel):
    text_content: str | None = None
    options: dict | None = None


class FlowNodeInput(BaseModel):
    user_input: UserInput
    internal_data_objs: list[InternalDataObjParams]
    resources: list[Resource]
    action: FlowNodeInputActionEnum


class NodeTypeEnum(str, Enum):
    ai_model_sync = "ai_model_sync"
    ai_model_stream = "ai_model_stream"
    ai_model_async = "ai_model_async"
    rag_index = "rag_index"
    rag_query = "rag_query"
    stream = "stream"


class PromptOptionsSettings(BaseModel):
    system_instructions: list[str] | None = None
    pre_prompt: list[str] | None = None
    prompt: list[str] | None = None
    post_prompt: list[str] | None = None
    options_overrides: dict | None = None

    def get_full_prompt(self, user_prompt: str | None = None) -> str:
        if self.prompt:
            return " ".join(self.prompt)
        parts = []
        if self.pre_prompt:
            parts.extend(self.pre_prompt)
        if user_prompt:
            parts.append(user_prompt)
        if self.post_prompt:
            parts.extend(self.post_prompt)
        return " ".join(parts)


class Node(BaseModel):
    identifier: str = Field(..., min_length=1, pattern="^[a-zA-Z0-9_-]+$")
    type: NodeTypeEnum
    order: int = Field(..., ge=0)
    resources: list[Resource] | None = None
    prompt_options_settings: PromptOptionsSettings | None = None
    subflow: "FlowDefinition | None" = None


class FlowDefinition(BaseModel):
    nodes: list[Node]
    execution_strategy: str
    prompt_options_settings: PromptOptionsSettings | None = None

    def validate_all_identifiers(self):
        ids = set()
        for node in self.nodes:
            if node.identifier in ids:
                raise ValueError(f"Duplicate identifier: {node.identifier}")
            ids.add(node.identifier)
