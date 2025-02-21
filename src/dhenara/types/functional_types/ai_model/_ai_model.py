from typing import Any

from pydantic import Field, model_validator

from dhenara.types.base import BaseModel
from dhenara.types.external_api._providers import AIModelFunctionalTypeEnum, AIModelProviderEnum


class ValidOptionValue(BaseModel):
    """
    Represents a valid option configuration for an AI model parameter.
    """

    allowed_values: list[Any] = Field(
        ...,
        description="List of allowed values for this option",
    )
    default_value: Any = Field(
        ...,
        description="Default value for this option",
    )
    cost_sensitive: bool = Field(
        ...,
        description="Will this option affect api-cost or not",
    )
    description: str | None = Field(
        None,
        description="Optional description of what this option controls",
    )

    @model_validator(mode="after")
    def validate_default_in_allowed_values(self) -> "ValidOptionValue":
        """Ensures the default value is among allowed values."""
        if self.default_value not in self.allowed_values:
            raise ValueError(
                f"Default value {self.default_value} must be one of {self.allowed_values}",
            )
        return self


class ChatModelSettings(BaseModel):
    max_context_window_tokens: int | None = Field(
        None,
        description="Maximum context window size in tokens",
    )
    max_input_tokens: int | None = Field(
        None,
        description="Maximum input tokens allowed",
    )
    max_output_tokens: int | None = Field(
        None,
        description="Maximum output tokens allowed",
    )

    @model_validator(mode="after")
    def _set_token_limits(self) -> "ChatModelSettings":
        if not self.max_output_tokens:
            raise ValueError("set_token_limits: max_output_tokens must be specified")
        if not (self.max_input_tokens or self.max_context_window_tokens):
            raise ValueError("set_token_limits: max_input_tokens or max_context_window_tokens must be specified")

        if self.max_input_tokens:
            self.max_context_window_tokens = self.max_input_tokens + self.max_output_tokens
        else:
            self.max_input_tokens = self.max_context_window_tokens - self.max_output_tokens

        return self


class ImageModelSettings(BaseModel):
    max_words: int | None = Field(
        None,
        description="Maximum word count, if applicable",
    )


class BaseAIModel(BaseModel):
    """
    Pydantic model representing an AI model configuration with options validation.
    """

    provider: AIModelProviderEnum = Field(
        ...,
        description="The AI model provider",
    )
    functional_type: AIModelFunctionalTypeEnum = Field(
        ...,
        description="Type of AI model functionality",
    )
    model_name: str = Field(
        ...,
        max_length=300,
        description="Model name used in API calls",
    )
    display_name: str = Field(
        ...,
        max_length=300,
        description="Display name for the model",
    )

    order: int = Field(
        0,
        description="Order for display purposes",
    )
    enabled: bool = Field(
        True,  # noqa: FBT003
        description="Whether the model is enabled",
    )
    beta: bool = Field(
        False,  # noqa: FBT003
        description="Whether the model is in beta",
    )

    settings: ChatModelSettings | ImageModelSettings | None = Field(
        default=None,
        description="Settings",
    )
    valid_options: dict[str, ValidOptionValue] | None = Field(
        default=None,
        description="Configured valid options and their allowed values",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata if needed",
    )
    reference_number: str | None = Field(
        None,
        description="Optional unique reference number",
    )

    @property
    def is_foundation_model(self) -> bool:
        return isinstance(self, FoundationModel)

    @model_validator(mode="after")
    def _validate_model_options(self) -> "BaseAIModel":
        """Validates model options against foundation model if present."""
        if self.is_foundation_model:
            return self

        if not self.foundation_model:
            return self

        # Validate that all options are present in foundation model
        invalid_options = set(self.valid_options.keys()) - set(
            self.foundation_model.valid_options.keys(),
        )
        if invalid_options:
            raise ValueError(
                f"Invalid options found: {invalid_options}. Must be subset of foundation model options.",
            )

        # Validate option values against foundation model
        for option_name, option_config in self.valid_options.items():
            foundation_config = self.foundation_model.valid_options[option_name]
            invalid_values = set(option_config.allowed_values) - set(
                foundation_config.allowed_values,
            )
            if invalid_values:
                raise ValueError(
                    f"Invalid values for option {option_name}: {invalid_values}",
                )

        return self

    @model_validator(mode="after")
    def _validate_settings(self) -> "BaseAIModel":
        if not self.settings:
            return self

        if self.functional_type == AIModelFunctionalTypeEnum.TEXT_GENERATION and not isinstance(self.settings, ChatModelSettings):
            raise ValueError("Settings should be instance of ChatModelSettings for chat models")

        if self.functional_type == AIModelFunctionalTypeEnum.IMAGE_GENERATION and not isinstance(self.settings, ImageModelSettings):
            raise ValueError("Settings should be instance of ImageModelSettings for image models")

        return self

    @model_validator(mode="after")
    def _validate_names(self) -> "BaseAIModel":
        if not self.display_name:
            self.display_name = self.model_name

        return self

    def validate_options(self, options: dict[str, Any]) -> bool:
        """
        Validates if the provided options conform to the model's valid options.

        Args:
            options: Dictionary of option name to value mappings

        Returns:
            bool: True if options are valid, False otherwise
        """
        try:
            self._validate_options_strict(options)
            return True
        except ValueError:
            return False

    def _validate_options_strict(self, options: dict[str, Any]) -> None:
        """
        Strictly validates options and raises ValueError for invalid options.

        Args:
            options: Dictionary of option name to value mappings

        Raises:
            ValueError: If any option is invalid
        """
        invalid_options = set(options.keys()) - set(self.valid_options.keys())
        if invalid_options:
            raise ValueError(f"Unknown options: {invalid_options}")

        for option_name, value in options.items():
            valid_values = self.valid_options[option_name].allowed_values
            if value not in valid_values:
                raise ValueError(
                    f"Invalid value for {option_name}: {value}. Must be one of {valid_values}",
                )

    def get_options_with_defaults(self, options: dict[str, Any]) -> dict[str, Any]:
        """
        Returns a complete options dictionary with defaults for missing values.

        Args:
            options: Partial options dictionary

        Returns:
            dict: Complete options dictionary with defaults
        """
        self._validate_options_strict(options)

        complete_options = {}
        for option_name, option_config in self.valid_options.items():
            complete_options[option_name] = options.get(
                option_name,
                option_config.default_value,
            )

        return complete_options


class FoundationModel(BaseAIModel):
    """
    Represents a foundation model that defines base capabilities and options.
    """

    pass


class AIModel(BaseAIModel):
    foundation_model: FoundationModel | None = Field(
        None,
        description="Matching foundation model for parameter preloading",
    )
