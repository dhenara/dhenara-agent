from dhenara.types.base import BaseEnum


class AiModelProvider(BaseEnum):
    CUSTOM = "custom"
    OPEN_AI = "open_ai"
    GOOGLE_AI = "google_ai"
    ANTHROPIC = "anthropic"
    META = "meta"
    COHERE = "cohere"
