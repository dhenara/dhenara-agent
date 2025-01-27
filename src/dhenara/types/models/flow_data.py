from enum import Enum

from pydantic import Field, model_validator

from ..base import BaseModel


class InternalDataModelTypeEnum(str, Enum):
    """Enumeration of available internal data model types."""

    conversation = "conversation"
    conversation_node = "conversation_node"
    conversation_space = "conversation_space"


class InternalDataObjParamsScopeEnum(str, Enum):
    """Enumeration of object scope types for internal data."""

    current = "current"
    parent = "parent"


class InternalDataObjParams(BaseModel):
    """
    Parameters for internal data objects with validation rules for different model types.

    Attributes:
        model_type: The type of internal data model
        object_id: Unique identifier for the object
        object_scope: Scope of the object (current or parent)
    """

    model_type: InternalDataModelTypeEnum = Field(
        ...,
        description="Type of the internal data model",
    )
    object_id: str = Field(
        ...,
        description="Unique identifier for the object",
    )
    object_scope: InternalDataObjParamsScopeEnum = Field(
        ...,
        description="Scope of the object (current or parent)",
    )

    @model_validator(mode="after")
    def validate_scope_based_on_model_type(self) -> "InternalDataObjParams":
        if self.model_type == InternalDataModelTypeEnum.conversation_node:
            if self.object_scope not in [InternalDataObjParamsScopeEnum.current, InternalDataObjParamsScopeEnum.parent]:
                raise ValueError("Conversation nodes must have either 'current' or 'parent' scope")
        else:
            if self.object_scope != InternalDataObjParamsScopeEnum.current:
                raise ValueError(f"{self.model_type} must have 'current' scope")
        return self


class ResourceModelTypeEnum(str, Enum):
    """Enumeration of available resource model types."""

    ai_model_endpoint = "ai_model_endpoint"
    rag_endpoint = "rag_endpoint"
    search_endpoint = "search_endpoint"


class Resource(BaseModel):
    """
    Resource configuration model with mutually exclusive fields for object parameters
    or fetch query.

    Attributes:
        model_type: Type of the resource model
        object_id: Unique identifier for the resource
        query: Optional query string for fetching resource details
    """

    model_type: ResourceModelTypeEnum = Field(
        ...,
        description="Type of the resource model",
    )
    object_id: str = Field(
        ...,
        description="Unique identifier for the resource",
    )
    query: str | None = Field(
        default=None,
        description="Query string for fetching resource details",
        examples=["{'api_model_name': 'claude-sonet-3.5-v2'}"],
    )

    @model_validator(mode="after")
    def validate_exclusive_fields(self) -> "Resource":
        if bool(self.object_params) == bool(self.query):
            raise ValueError("Exactly one of object_params or query must be provided")
        return self


class FlowNodeInputActionEnum(str, Enum):
    """Enumeration of available API call actions."""

    generate_conversation_node = "generate_conversation_node"
    regenerate_conversation_node = "regenerate_conversation_node"
    delete_conversation_node = "delete_conversation_node"


class UserInput(BaseModel):
    """
    User input model for AI model calls.

    Attributes:
        text_content: Optional question text
        options: Optional dictionary of AI model specific options
    """

    text_content: str | None = Field(
        default=None,
        description="Question text for the AI model",
    )
    options: dict | None = Field(
        default=None,
        description="Additional options for the AI model",
    )
    # TODO files:


class FlowNodeInput(BaseModel):
    """
    Input model for execution nodes with validation rules for different actions.

    Attributes:
        user_input: User input for AI model or RAG
        internal_data_objs: List of internal data objects
        resources: List of resources to be used
        action: Type of API action to perform
    """

    user_input: UserInput = Field(  # TODO: |RagUserInput
        ...,
        description="User input for the execution",
    )

    internal_data_objs: list[InternalDataObjParams] = Field(
        ...,
        description="List of internal data objects",
    )
    resources: list[Resource] = Field(
        ...,
        description="List of resources to be used",
    )
    action: FlowNodeInputActionEnum = Field(
        ...,
        description="Type of API action to perform",
    )

    @model_validator(mode="after")
    def validate_action_requirements(self) -> "FlowNodeInput":
        node_objects = [obj for obj in self.internal_data_objs if obj.model_type == InternalDataModelTypeEnum.conversation_node]

        if self.action == FlowNodeInputActionEnum.regenerate_conversation_node:
            current_nodes = [obj for obj in node_objects if obj.object_scope == InternalDataObjParamsScopeEnum.current]
            parent_nodes = [obj for obj in node_objects if obj.object_scope == InternalDataObjParamsScopeEnum.parent]

            if not (len(current_nodes) == 1 and len(parent_nodes) == 1):
                raise ValueError("Regenerate action requires exactly one current and one parent node")

        return self


class FlowNodeExecutionStatusEnum(str, Enum):
    """Enumeration of possible execution statuses."""

    success = "success"
    failed = "failed"
    pending = "pending"


class FlowNodeOutputActionEnum(str, Enum):
    """Enumeration of available API call actions."""

    save_content_to_conversation_node = "save_content_to_conversation_node"
    update_conversation_node_title = "update_conversation_node_title"
    delete_conversation_node = "delete_conversation_node"


class FlowNodeOutput(BaseModel):
    """
    Output model for execution nodes.

    Attributes:
        raw_output: List of raw output strings
        output_objects: List of output objects
        execution_status: Status of the execution
        metadata: Optional metadata dictionary
    """

    raw_output: list[str] = Field(
        ...,
        description="List of raw output strings",
    )

    internal_data_objs: list[InternalDataObjParams] = Field(
        ...,
        description="List of internal data objects",
    )

    action: FlowNodeOutputActionEnum = Field(
        ...,
        description="Type of action to perform",
    )

    execution_status: FlowNodeExecutionStatusEnum = Field(
        ...,
        description="Status of the execution",
    )
    metadata: dict | None = Field(
        default=None,
        description="Additional metadata about the execution",
    )
