# ruff: noqa: E501
from typing import Literal

from dhenara.types.functional_types.ai_model import AIModelFunctionalTypeEnum, AIModelProviderEnum, FoundationModel, ValidOptionValue

Dalle3 = FoundationModel(
    model_name="dall-e-3",
    foundation_model_name="dall-e-3",
    functional_type=AIModelFunctionalTypeEnum.IMAGE_GENERATION,
    max_context_window_tokens=None,
    max_input_tokens=None,
    max_output_tokens=None,
    valid_options={
        "quality": ValidOptionValue(
            allowed_values=["standard", "hd"],
            default_value="standard",
            cost_sensitive=True,
            description="Image quality setting",
        ),
        "size": ValidOptionValue(
            allowed_values=["1024x1024", "1024x1792", "1792x1024"],
            default_value="1024x1024",
            cost_sensitive=True,
            description="Output image dimensions",
        ),
        "style": ValidOptionValue(
            allowed_values=["natural", "vivid"],
            default_value="natural",
            cost_sensitive=False,
            description="Image style preference",
        ),
        "n": ValidOptionValue(
            allowed_values=[1],
            default_value=1,
            cost_sensitive=True,
            description="Number of images to generate",
        ),
        "response_format": ValidOptionValue(
            allowed_values=Literal["b64_json", "url"],
            default_value="url",
            cost_sensitive=False,
            description="Response format",
        ),
    },
    meta={
        "display_order": 51,
        "details": "DALL·E model released in Nov 2023.",
        "max_word_count": 4000,
    },
)

FOUNDATION_MODELS_MAPPINGS = [
    {
        AIModelFunctionalTypeEnum.TEXT_GENERATION: {
            # https://platform.openai.com/docs/models
            AIModelProviderEnum.OPEN_AI: [],
            # https://ai.google.dev/gemini-api/docs/models/gemini
            AIModelProviderEnum.GOOGLE_AI: [],
            # https://docs.anthropic.com/en/docs/about-claude/models
            AIModelProviderEnum.ANTHROPIC: [],
            AIModelProviderEnum.DEEPSEEK: [],
        },
        AIModelFunctionalTypeEnum.IMAGE_GENERATION: {
            AIModelProviderEnum.OPEN_AI: [Dalle3],
            AIModelProviderEnum.GOOGLE_AI: [],
        },
    },
]
