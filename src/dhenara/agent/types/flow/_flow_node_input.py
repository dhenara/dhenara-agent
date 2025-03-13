from typing import Any

from pydantic import Field, field_validator

from dhenara.agent.types.flow import SpecialNodeIdEnum
from dhenara.ai.types.shared.base import BaseModel

SystemInstructions = list[str]


class TODOSystemInstructions(BaseModel):
    """Configuration for system-level AI instructions.

    This model defines the structure for system instructions provided to the AI model.

    Attributes:
        system_instructions: System-level instructions for the AI model as list of strings
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "system_instructions": ["You are a helpful assistant"],
                },
            ],
        },
    }


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
        description="Default values for template variables if not provided at runtime",
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

        # Special kw inputs
        # dh_user_input = kwargs.pop("dh_user_input", None)

        # Start with default values and override with runtime values
        format_values = {}
        if self.default_values:
            format_values.update(self.default_values)
        if kwargs:
            format_values.update(kwargs)

        # Format template with variables
        if format_values:
            return self.template.format(**format_values)
        return self.template

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


class AISettings(BaseModel):
    """Configuration for AI model options and settings.

    This model defines the structure for configuring AI model options and settings.

    Attributes:
        options_overrides: Override options for AI model API calls
    """

    system_instructions: SystemInstructions = Field(
        default_factory=list,
        description="Node specific system instructions",
    )

    node_prompt: PromptTemplate | None = Field(
        default=None,
        description="Node specific prompts generation sinstruction/option parameters",
    )
    options_overrides: dict[str, Any] | None = Field(
        default=None,
        default_factory=None,
        description="Options to override default AI model API call parameters",
    )

    def get_system_instructions(self) -> str | None:
        """Returns the system instructions if set.

        Returns:
            str | None: Joined system instructions or None if not set
        """
        if self.system_instructions:
            return " ".join(self.system_instructions)
        return None

    def get_options(self, user_options: dict[str, Any] | None = None) -> dict[str, Any]:
        """Returns the merged options dictionary.

        Args:
            user_options: Optional user provided options to merge with overrides

        Returns:
            dict[str, Any]: Merged options with overrides taking precedence
        """
        if user_options is None:
            return self.options_overrides or {}

        if self.options_overrides:
            merged = user_options.copy()
            merged.update(self.options_overrides)
            return merged

        return user_options


class NodeInputSource(BaseModel):
    """Configuration for input sources of a flow node.

    Defines how a node receives input data through two types of sources:
    1. User input sources: Initial user input or specific node inputs
    2. Node output sources: Previous node output or specific node outputs

    Attributes:
        user_input_sources: Sources for user input data
        context_sources: Sources for context from previous node output data

    Examples:
        >>> source = NodeInputSource(
        user_input_sources=["initial_user_input", "input_node_1"],
        context_sources=["previous", "node_1"],
    )
    """

    user_input_sources: list[str] = Field(
        default_factory=list,
        description=(f"List of node IDs or special identifiers to collect user input from. Use '{SpecialNodeIdEnum.FULL}' for complete initial user input"),
        example=["initial_user_input", "input_node_1"],
    )

    context_sources: list[str] = Field(
        default_factory=list,
        description=(
            f"List of node IDs or special identifiers to collect node output from. "
            "Note that this will be passed as context to the current node model call"
            f"Use '{SpecialNodeIdEnum.PREVIOUS}' for previous node output"
        ),
        example=["previous", "node_1", "node_2"],
    )

    @field_validator("user_input_sources", "context_sources")
    @classmethod
    def validate_source_ids(cls, source_ids: list[str]) -> list[str]:
        """Validate that source IDs are non-empty strings."""
        if any(not source_id.strip() for source_id in source_ids):
            raise ValueError("Source IDs must be non-empty strings")
        return [source_id.strip() for source_id in source_ids]

    def validate_node_references(self, available_node_ids: list[str]) -> bool:
        """Validate that all referenced node IDs exist in the flow.

        Args:
            available_node_ids: List of all valid node IDs in the flow

        Returns:
            bool: True if all references are valid

        Raises:
            ValueError: If any referenced node ID is invalid
        """

        # Validate user input sources
        invalid_user_inputs = {source_id for source_id in self.user_input_sources if source_id not in available_node_ids and source_id != SpecialNodeIdEnum.FULL.value}
        if invalid_user_inputs:
            raise ValueError(
                f"Invalid user input source IDs: {', '.join(invalid_user_inputs)}",
            )

        # Validate node output sources
        invalid_node_outputs = {source_id for source_id in self.context_sources if source_id not in available_node_ids and source_id != SpecialNodeIdEnum.PREVIOUS.value}
        if invalid_node_outputs:
            raise ValueError(
                f"Invalid node output source IDs: {', '.join(invalid_node_outputs)}",
            )

        return True

    @property
    def uses_previous_node(self) -> bool:
        """Check if the node uses output from the previous node."""
        return SpecialNodeIdEnum.PREVIOUS.value in self.context_sources

    @property
    def uses_initial_user_input(self) -> bool:
        """Check if the node uses complete initial user input."""
        return SpecialNodeIdEnum.FULL.value in self.user_input_sources

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_input_sources": ["initial_user_input", "input_node_1"],
                    "context_sources": ["previous", "node_1", "node_2"],
                },
                {
                    "user_input_sources": ["input_node_1"],
                    "context_sources": ["node_1"],
                },
            ],
        },
    }


class NodeInputSettings(BaseModel):
    input_source: NodeInputSource | None = Field(
        ...,
        description="Input Source",
    )
