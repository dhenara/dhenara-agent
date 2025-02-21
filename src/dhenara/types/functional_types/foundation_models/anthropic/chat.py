from dhenara.types.functional_types.ai_model import (
    AIModelFunctionalTypeEnum,
    AIModelProviderEnum,
    ChatModelSettings,
    FoundationModel,
)

Claude35Haiku = FoundationModel(
    model_name="claude-3-5-haiku",
    display_name="Claude Haiku 3.5",
    provider=AIModelProviderEnum.ANTHROPIC,
    functional_type=AIModelFunctionalTypeEnum.TEXT_GENERATION,
    settings=ChatModelSettings(
        max_context_window_tokens=200000,
        max_output_tokens=8192,
    ),
    valid_options={},
    metadata={
        "details": "Fastest, most cost-effective model.",
    },
    order=20,
)


Claude35Sonnet = FoundationModel(
    model_name="claude-3-5-sonnet",
    display_name="Claude Sonnet 3.5",
    provider=AIModelProviderEnum.ANTHROPIC,
    functional_type=AIModelFunctionalTypeEnum.TEXT_GENERATION,
    settings=ChatModelSettings(
        max_context_window_tokens=200000,
        max_output_tokens=8192,
    ),
    valid_options={},
    metadata={
        "details": "Model, with highest level of intelligence and capability.",
    },
    order=21,
)


Claude3Opus = FoundationModel(
    model_name="claude-3-opus",
    display_name="Claude 3 Opus",
    provider=AIModelProviderEnum.ANTHROPIC,
    functional_type=AIModelFunctionalTypeEnum.TEXT_GENERATION,
    settings=ChatModelSettings(
        max_context_window_tokens=200000,
        max_output_tokens=4096,
    ),
    valid_options={},
    metadata={
        "details": "Powerful model for highly complex tasks",
    },
    order=12,
)

CHAT_MODELS = [Claude35Sonnet, Claude35Haiku, Claude3Opus]
