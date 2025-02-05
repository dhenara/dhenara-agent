from typing import Any

from pydantic import Field, field_validator, model_validator

from dhenara.types.base import BaseModel
from dhenara.types.flow import SpecialNodeIdEnum

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


class NodePrompt(BaseModel):
    """Configuration for AI prompts.

    This model defines the structure for configuring AI prompts.
    Either direct prompt or pre/post prompts can be used.

    Attributes:
        pre_prompt: Text to prepend to user prompt as list of strings
        prompt: Direct prompt text as list of strings
        post_prompt: Text to append to user prompt as list of strings
    """

    pre_prompt: list[str] | None = Field(
        default=None,
        default_factory=None,
        description="Text that will be prepended to the user's prompt",
    )

    prompt: list[str] | None = Field(
        default=None,
        default_factory=None,
        description="Direct prompt text to send to the AI model",
    )

    post_prompt: list[str] | None = Field(
        default=None,
        default_factory=None,
        description="Text that will be appended to the user's prompt",
    )

    @model_validator(mode="after")
    def validate_prompt_configuration(self) -> "NodePrompt":
        """Validates that either prompt or pre/post prompt is provided."""
        if self.prompt and (self.pre_prompt or self.post_prompt):
            raise ValueError("Both 'prompt' and 'pre_prompt'/'post_prompt' are not allowed")
        return self

    def get_full_prompt(self, user_prompt: str | None = None) -> str:
        """Constructs and returns the full prompt by combining pre/post prompts.

        Args:
            user_prompt: Optional user provided prompt to combine with pre/post prompts

        Returns:
            str: The complete prompt text
        """
        if self.prompt is not None:
            return " ".join(self.prompt)

        parts = []
        if self.pre_prompt:
            parts.extend(self.pre_prompt)
        if user_prompt:
            parts.append(user_prompt)
        if self.post_prompt:
            parts.extend(self.post_prompt)

        return " ".join(parts)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "pre_prompt": ["Please answer the following question:"],
                    "post_prompt": ["Provide a detailed explanation."],
                },
                {
                    "prompt": ["What is the capital of France?"],
                },
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

    node_prompt: NodePrompt | None = Field(
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
        node_output_sources: Sources for node output data

    Examples:
        >>> source = NodeInputSource(user_input_sources=["initial_user_input", "input_node_1"], node_output_sources=["previous", "node_1"])
    """

    user_input_sources: list[str] = Field(
        default_factory=list,
        description=(f"List of node IDs or special identifiers to collect user input from. Use '{SpecialNodeIdEnum.FULL}' for complete initial user input"),
        example=["initial_user_input", "input_node_1"],
    )

    node_output_sources: list[str] = Field(
        default_factory=list,
        description=(f"List of node IDs or special identifiers to collect node output from. Use '{SpecialNodeIdEnum.PREVIOUS}' for previous node output"),
        example=["previous", "node_1", "node_2"],
    )

    @field_validator("user_input_sources", "node_output_sources")
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
        invalid_node_outputs = {source_id for source_id in self.node_output_sources if source_id not in available_node_ids and source_id != SpecialNodeIdEnum.PREVIOUS.value}
        if invalid_node_outputs:
            raise ValueError(
                f"Invalid node output source IDs: {', '.join(invalid_node_outputs)}",
            )

        return True

    @property
    def uses_previous_node(self) -> bool:
        """Check if the node uses output from the previous node."""
        return SpecialNodeIdEnum.PREVIOUS.value in self.node_output_sources

    @property
    def uses_initial_user_input(self) -> bool:
        """Check if the node uses complete initial user input."""
        return SpecialNodeIdEnum.FULL.value in self.user_input_sources

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_input_sources": ["initial_user_input", "input_node_1"],
                    "node_output_sources": ["previous", "node_1", "node_2"],
                },
                {
                    "user_input_sources": ["input_node_1"],
                    "node_output_sources": ["node_1"],
                },
            ],
        },
    }


class NodeInputSettings(BaseModel):
    input_source: NodeInputSource | None = Field(
        ...,
        description="Input Source",
    )
