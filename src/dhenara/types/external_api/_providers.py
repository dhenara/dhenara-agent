from dhenara.types.base import BaseEnum


class AiModelProvider(BaseEnum):
    CUSTOM = "custom"
    OPEN_AI = "open_ai"
    GOOGLE_AI = "google_ai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    META = "meta"
    COHERE = "cohere"


class AiModelAPIProvider(BaseEnum):
    OPEN_AI = "openai"
    GOOGLE_AI = "google_gemini_api"
    ANTHROPIC = "anthropic"
    GOOGLE_VERTEX_AI = "google_vertex_ai"
    MICROSOFT_AZURE_AI = "microsoft_azure_ai"
    AMAZON_BEDROCK = "amazon_bedrock"
    DEEPSEEK = "deepseek"
