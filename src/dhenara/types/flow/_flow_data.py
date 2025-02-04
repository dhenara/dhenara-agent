from pydantic import Field, model_validator

from dhenara.types.base import BaseEnum, BaseModel
from dhenara.types.flow import UserInput


class InternalDataObjectTypeEnum(BaseEnum):
    """Enumeration of available internal data model types."""

    conversation = "conversation"
    conversation_node = "conversation_node"
    conversation_space = "conversation_space"


class InternalDataObjParamsScopeEnum(BaseEnum):
    """Enumeration of object scope types for internal data."""

    current = "current"
    parent = "parent"


class InternalDataObjParams(BaseModel):
    """
    Parameters for internal data objects with validation rules for different model types.

    Attributes:
        object_type: The type of internal data model
        object_id: Unique identifier for the object
        object_scope: Scope of the object (current or parent)
    """

    object_type: InternalDataObjectTypeEnum = Field(
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
    def validate_scope_based_on_object_type(self) -> "InternalDataObjParams":
        if self.object_type == InternalDataObjectTypeEnum.conversation_node:
            if self.object_scope not in [InternalDataObjParamsScopeEnum.current, InternalDataObjParamsScopeEnum.parent]:
                raise ValueError("Conversation nodes must have either 'current' or 'parent' scope")
        else:
            if self.object_scope != InternalDataObjParamsScopeEnum.current:
                raise ValueError(f"{self.object_type} must have 'current' scope")
        return self


class ResourceObjectTypeEnum(BaseEnum):
    """Enumeration of available resource model types."""

    ai_model_endpoint = "ai_model_endpoint"
    rag_endpoint = "rag_endpoint"
    search_endpoint = "search_endpoint"


RESOURCE_MODEL_QUERY_MAPPING = {
    ResourceObjectTypeEnum.ai_model_endpoint: [
        "ai_model__api_model_name",
    ]
}


class Resource(BaseModel):
    """
    Resource configuration model with mutually exclusive fields for object parameters
    or fetch query.

    Attributes:
        object_type: Type of the resource model
        object_id: Unique identifier for the resource
        query: Optional query string for fetching resource details
    """

    object_type: ResourceObjectTypeEnum = Field(
        ...,
        description="Type of the resource model",
    )
    object_id: str | None = Field(
        default=None,
        description="Unique identifier for the resource",
    )
    query: dict | None = Field(
        default=None,
        description="Query dict for fetching resource details",
        examples=["{'api_model_name': 'claude-sonet-3.5-v2'}"],
    )
    is_default: bool = Field(
        default=False,
        description="Is default resource or not. Only one default is allowed in a list of resources",
    )

    @model_validator(mode="after")
    def validate_exclusive_fields(self) -> "Resource":
        if self.object_id and self.query:
            raise ValueError("Exactly one of object_type+object_id, or query is allowed")

        # Validate query keys based on model type
        for key in self.query.keys():
            query_mapping = RESOURCE_MODEL_QUERY_MAPPING.get(self.object_type)
            if key not in query_mapping:
                raise ValueError(f"Unsupported query key `{key}`")

        return self


class FlowNodeInputActionEnum(BaseEnum):
    """Enumeration of available API call actions."""

    generate_conversation_node = "generate_conversation_node"
    regenerate_conversation_node = "regenerate_conversation_node"
    delete_conversation_node = "delete_conversation_node"


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
        default_factory=list,
        description="List of internal data objects",
    )
    resources: list[Resource] = Field(
        default_factory=list,
        description="List of resources to be used",
    )
    action: FlowNodeInputActionEnum | None = Field(
        default=None,
        description="Type of API action to perform, if any",
    )

    # NOTE:
    # `is_default` validations for resoures are added inside flow models,
    # note input models

    @model_validator(mode="after")
    def validate_action_requirements(self) -> "FlowNodeInput":
        node_objects = [obj for obj in self.internal_data_objs if obj.object_type == InternalDataObjectTypeEnum.conversation_node]

        if self.action == FlowNodeInputActionEnum.regenerate_conversation_node:
            current_nodes = [obj for obj in node_objects if obj.object_scope == InternalDataObjParamsScopeEnum.current]
            parent_nodes = [obj for obj in node_objects if obj.object_scope == InternalDataObjParamsScopeEnum.parent]

            if not (len(current_nodes) == 1 and len(parent_nodes) == 1):
                raise ValueError("Regenerate action requires exactly one current and one parent node")

        return self


class FlowNodeExecutionStatusEnum(BaseEnum):
    """Enumeration of possible execution statuses."""

    success = "success"
    failed = "failed"
    pending = "pending"


class FlowNodeOutputActionEnum(BaseEnum):
    """Enumeration of available API call actions."""

    def __str__(self):
        return self.value

    # Conversation Node Actions
    save_to_conversation_node = "save_to_conversation_node"
    update_conversation_node_title = "update_conversation_node_title"
    delete_conversation_node = "delete_conversation_node"
    # Response
    send_result = "send_result"
    send_status = "send_status"
    send_result_and_status = "send_result_and_status"
    send_ack = "send_ack"
    send_push_notification = "send_push_notification"


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
        min_items=0,
    )
    internal_data_objs: list[InternalDataObjParams] = Field(
        ...,
        description="List of internal data objects",
        min_items=0,
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
