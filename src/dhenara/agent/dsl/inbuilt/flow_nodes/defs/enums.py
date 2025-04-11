from dhenara.agent.types.base import BaseEnum


class FlowNodeTypeEnum(BaseEnum):
    command = "command"
    folder_analyzer = "folder_analyzer"
    file_operation = "file_operation"
    git_repo_analyzer = "git_repo_analyzer"
    ai_model_call = "ai_model_call"
    ai_model_call_stream = "ai_model_call_stream"
    rag_index = "rag_index"
    rag_query = "rag_query"
    custom = "custom"


# TODO_FUTURE: Some of the deterministic node types to implement
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
