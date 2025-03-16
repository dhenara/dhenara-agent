from typing import Any

from pydantic import Field

from dhenara.ai.types.shared.base import BaseModel

# class SystemInstructions(BaseModel):
#    pass

SystemInstructions = list[str]


class PromptTemplate(BaseModel):
    """Template configuration for AI interactions.

    A generic template structure for configuring various AI interaction texts,
    including prompts, system instructions, context information, or any templated text.
    Supports dynamic variable substitution through standard Python string formatting.

    Attributes:
        template: The text template with optional placeholders for formatting
        default_values: Optional dictionary of default values for template variables
    """

    template: str = Field(
        description="Text template with optional {placeholders} for string formatting",
    )

    default_values: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Default values for template variables if not provided at runtime"
            "Use variable `dh_input_content` to insert input content"
        ),
    )

    def format(self, **kwargs) -> str:
        """Formats the template with provided values.

        Additional keyword arguments can be passed at runtime to be included
        in the template formatting, overriding any matching keys in the
        default_values dictionary.

        Args:
            **kwargs: Runtime values for template variables (overrides defaults)

        Returns:
            str: The complete formatted text
        """
        # Start with default values and override with runtime values
        format_values = {}
        if self.default_values:
            format_values.update(self.default_values)
        if kwargs:
            format_values.update(kwargs)

        # Get the template we'll be working with
        template_text = self.template

        # Handle special placeholders
        # TODO_FUTURE: Use `jinja2` for processing specail jinja2 and remove if not present
        # special_placeholders = {
        #    "dh_input_content": self._handle_input_content,
        #    # more special placeholders and their handlers here
        # }

        # Format template with variables
        if format_values:
            return template_text.format(**format_values)
        return template_text

    model_config = {
        "json_schema_extra": {
            "examples": [
                # Example as user prompt
                {
                    "template": "Write a {length} essay about {topic}.",
                    "default_values": {
                        "length": "short",
                        "topic": "artificial intelligence",
                    },
                },
                # Example as system instruction
                {"template": "You are an AI assistant specialized in {domain}. Always format responses as {format}."},
                # Example as context information
                {"template": "Here is some background information: {context}"},
            ],
        },
    }
