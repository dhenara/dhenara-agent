from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, field_validator

from dhenara.agent.types.data import PromptTemplate, SystemInstructions
from dhenara.agent.types.flow import SpecialNodeIdEnum
from dhenara.ai.types.shared.base import BaseModel


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
    structured_output: type[PydanticBaseModel] | None = Field(
        default=None,
        description="Structured output model for the AI model response",
    )
    options_overrides: dict[str, Any] | None = Field(
        default=None,
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


class NodeInputSettings(BaseModel):
    """Configuration for input sources of a flow node.

    Defines how a node receives input data through two types of sources:
    1. User input sources: Initial user input or specific node inputs
    2. Node output sources: Previous node output or specific node outputs

    Attributes:
        context_sources: Sources for context from previous node output data

    Examples:
        >>> setting = NodeInputSettings(
        context_sources=["previous", "node_1"],
    )
    """

    # content_sources: list[str] = Field(
    #    default_factory=list,
    #    description=(
    #        "List of node IDs or special identifiers to collect user input from. "
    #        f"Use '{SpecialNodeIdEnum.FULL}' for complete initial user input"
    #    ),
    #    example=["initial_content", "input_node_1"],
    # )

    context_sources: list[str] = Field(
        default_factory=list,
        description=(
            f"List of node IDs or special identifiers to collect node output from. "
            "Note that this will be passed as context to the current node model call"
            f"Use '{SpecialNodeIdEnum.PREVIOUS}' for previous node output"
        ),
        example=["previous", "node_1", "node_2"],
    )

    @field_validator("context_sources")
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

        ## Validate user input sources
        # invalid_contents = {
        #    source_id
        #    for source_id in self.content_sources
        #    if source_id not in available_node_ids and source_id != SpecialNodeIdEnum.FULL.value
        # }
        # if invalid_contents:
        #    raise ValueError(
        #        f"Invalid user input source IDs: {', '.join(invalid_contents)}",
        #    )

        # Validate node output sources
        invalid_node_outputs = {
            source_id
            for source_id in self.context_sources
            if source_id not in available_node_ids
            and source_id != SpecialNodeIdEnum.PREVIOUS.value
        }
        if invalid_node_outputs:
            raise ValueError(
                f"Invalid node output source IDs: {', '.join(invalid_node_outputs)}",
            )

        return True

    @property
    def uses_previous_node(self) -> bool:
        """Check if the node uses output from the previous node."""
        return SpecialNodeIdEnum.PREVIOUS.value in self.context_sources

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "context_sources": ["previous", "node_1", "node_2"],
                },
            ],
        },
    }
