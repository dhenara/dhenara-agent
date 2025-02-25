from dhenara.ai.types.shared.base import BaseEnum


class ContentType(BaseEnum):
    """Enumeration of content types that can be returned."""

    TEXT = "text"
    LIST = "list"
    DICT = "dict"
    JSONL = "jsonl"


class InternalDataObjectTypeEnum(BaseEnum):
    """Enumeration of available internal data model types."""

    conversation = "conversation"
    conversation_node = "conversation_node"
    conversation_space = "conversation_space"


class InternalDataObjParamsScopeEnum(BaseEnum):
    """Enumeration of object scope types for internal data."""

    current = "current"
    parent = "parent"


class SpecialNodeIdEnum(BaseEnum):
    """Special node identifiers for input sources."""

    PREVIOUS = "previous"  # Reference to previous node
    FULL = "full"  # Reference to complete user input


class ResourceObjectTypeEnum(BaseEnum):
    """Enumeration of available resource model types."""

    ai_model_endpoint = "ai_model_endpoint"
    rag_endpoint = "rag_endpoint"
    search_endpoint = "search_endpoint"


class ResourceQueryFieldsEnum(BaseEnum):
    """Enum defining all possible query fields for resources."""

    model_name = "model_name"
    model_display_name = "model_display_name"
    api_provider = "api_provider"


class ResourceQueryMapping:
    """Static Class defining the mapping between resource types and their allowed query fields."""

    MAPPINGS: dict[ResourceObjectTypeEnum, list[ResourceQueryFieldsEnum]] = {
        ResourceObjectTypeEnum.ai_model_endpoint: [
            ResourceQueryFieldsEnum.model_name,
            ResourceQueryFieldsEnum.model_display_name,
            ResourceQueryFieldsEnum.api_provider,
        ],
    }

    @classmethod
    def get_allowed_fields(cls, resource_type: ResourceObjectTypeEnum) -> list[str]:
        """
        Get allowed query fields for a resource type.

        Args:
            resource_type: The type of resource

        Returns:
            List of allowed field names
        """
        return [field.value for field in cls.MAPPINGS.get(resource_type, [])]


class FlowNodeUserInputActionEnum(BaseEnum):
    """Additional actions on the node ( on top of the ones in the node."""

    generate_conversation_node = "generate_conversation_node"
    regenerate_conversation_node = "regenerate_conversation_node"
    delete_conversation_node = "delete_conversation_node"


class FlowNodePreActionEnum(BaseEnum):
    pass


class FlowNodePostActionEnum(BaseEnum):
    """Enumeration of available API call actions."""

    pass


class StorageEntityTypeEnum(BaseEnum):
    """Type of storage entities in the conversation system."""

    conversation_node = "conversation_node"
    conversation = "conversation"
    conversation_space = "conversation_space"


class ConversationFieldEnum(BaseEnum):
    """Available fields for Conversation entities."""

    all = "all"
    title = "title"


class ConversationNodeFieldEnum(BaseEnum):
    """Available fields for ConversationNode entities."""

    all = "all"
    inputs = "inputs"
    refined_prompts = "refined_prompts"
    outputs = "outputs"
    meta = "meta"


class ConversationSpaceFieldEnum(BaseEnum):
    """Available fields for ConversationSpace entities."""

    all = "all"


class FlowExecutionStatusEnum(BaseEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionStrategyEnum(BaseEnum):
    """Enum defining execution strategy for flow nodes.

    Attributes:
        sequential: FlowNodes execute one after another in sequence
        parallel: FlowNodes execute simultaneously in parallel
    """

    sequential = "sequential"
    parallel = "parallel"


class FlowNodeTypeEnum(BaseEnum):
    """Enum defining types of flow nodes.

    Attributes:
        ai_model_call: Calls AI model API
        ai_model_call_stream: Calls AI model API with stream
        rag_index: RAG index creation operation
        rag_query: RAG query/retrieval operation
        stream: Generic streaming operation
    """

    ai_model_call = "ai_model_call"
    ai_model_call_stream = "ai_model_call_stream"
    rag_index = "rag_index"
    rag_query = "rag_query"
