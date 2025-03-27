from dhenara.agent.types.base import BaseEnum


class FlowNodeTypeEnum(BaseEnum):
    command = "command"
    folder_analyzer = "folder_analyzer"
    git_repo_analyzer = "git_repo_analyzer"
    ai_model_call = "ai_model_call"
    ai_model_call_stream = "ai_model_call_stream"
    rag_index = "rag_index"
    rag_query = "rag_query"
    custom = "custom"
