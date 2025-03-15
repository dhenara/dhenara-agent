from dhenara.ai.types.shared.base import BaseEnum


class SpecialNodeIdEnum(BaseEnum):
    """Special node identifiers for input sources."""

    PREVIOUS = "previous"  # Reference to previous node


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
    command = "command"  # To execute a unix command
    ai_model_call = "ai_model_call"
    ai_model_call_stream = "ai_model_call_stream"
    rag_index = "rag_index"
    rag_query = "rag_query"
    custom = "custom"


# TODO: Move
# -----------------------------------------------------------------------------
class InternalDataObjectTypeEnum(BaseEnum):
    """Enumeration of available internal data model types."""

    conversation = "conversation"
    conversation_node = "conversation_node"
    conversation_space = "conversation_space"


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
