from dhenara.ai.types.shared.base import BaseEnum


class SpecialNodeIdEnum(BaseEnum):
    """Special node identifiers for input sources."""

    PREVIOUS = "previous"  # Reference to previous node


class ExecutionStatusEnum(BaseEnum):
    """Generic execution status enum that can be used by any DSL component."""

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


class FlowTypeEnum(BaseEnum):
    standard = "standard"
    condition = "condition"  # If-else branching
    loop = "loop"  # Iteration
    switch = "switch"  # Multiple branching
    # custom = "custom"


class FlowNodeTypeEnum(BaseEnum):
    command = "command"  # To execute a unix command
    folder_analyzer = "folder_analyzer"
    git_repo_analyzer = "git_repo_analyzer"

    # AI Model
    ai_model_call = "ai_model_call"
    ai_model_call_stream = "ai_model_call_stream"

    # RAG: TODO: Not implemented
    rag_index = "rag_index"
    rag_query = "rag_query"

    # Custom
    custom = "custom"


# TODO_FUTURE:  deterministic node types to implement
class FUTUREFlowNodeTypeEnum(BaseEnum):
    # File operations
    file_reader = "file_reader"  # Read file content
    file_writer = "file_writer"  # Write content to a file
    json_processor = "json_processor"  # Process and transform JSON
    csv_processor = "csv_processor"  # Process CSV data

    # Web and API operations
    http_request = "http_request"  # Make HTTP requests
    api_client = "api_client"  # Interact with APIs

    # Data processing
    data_transformer = "data_transformer"  # Transform data (using jq or similar)
    text_extractor = "text_extractor"  # Extract text patterns

    # Code operations
    code_executor = "code_executor"  # Execute code (Python, JavaScript, etc.)
    code_analyzer = "code_analyzer"  # Static code analysis

    # Integration with tools
    database_query = "database_query"  # Execute database queries
    vector_store = "vector_store"  # Store/retrieve from vector databases


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
