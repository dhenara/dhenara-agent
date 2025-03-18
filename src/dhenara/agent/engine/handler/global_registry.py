# Global registry instance
from dhenara.agent.engine.handler import (
    AIModelCallHandler,
    AIModelCallStreamHandler,
    CommandHandler,
    CustomHandlerRegistry,
    FolderAnalyzerHandler,
    GitRepoAnalyzerHandler,
    NodeHandlerRegistry,
    RAGIndexHandler,
    RAGQueryHandler,
)
from dhenara.agent.types.flow import FlowNodeTypeEnum

node_handler_registry = NodeHandlerRegistry()

node_handler_registry.register(FlowNodeTypeEnum.command, CommandHandler)
node_handler_registry.register(FlowNodeTypeEnum.folder_analyzer, FolderAnalyzerHandler)
node_handler_registry.register(FlowNodeTypeEnum.git_repo_analyzer, GitRepoAnalyzerHandler)
node_handler_registry.register(FlowNodeTypeEnum.ai_model_call, AIModelCallHandler)
node_handler_registry.register(FlowNodeTypeEnum.ai_model_call_stream, AIModelCallStreamHandler)
node_handler_registry.register(FlowNodeTypeEnum.rag_index, RAGIndexHandler)
node_handler_registry.register(FlowNodeTypeEnum.rag_query, RAGQueryHandler)

# Global registry for custom handlers
custom_handler_registry = CustomHandlerRegistry()
