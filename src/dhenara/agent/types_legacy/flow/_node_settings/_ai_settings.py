from typing import Any

from pydantic import Field, field_validator

from dhenara.agent.types.flow import SpecialNodeIdEnum
from dhenara.ai.types.genai.dhenara.request import AIModelCallConfig
from dhenara.ai.types.shared.base import BaseModel


class NodeSettings(BaseModel):  # TODO: Rename to AIInputSettings
    pass


class LegacyAISettings(BaseModel):  # TODO: Rename to NodeSettings
    """Configuration for AI model options and settings.

    This model defines the structure for configuring AI model options and settings.
    """

    node_prompt: str = Field(
        default=None,
        description="Node specific prompts generation sinstruction/option parameters",
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
    system_instructions: list[str] = Field(
        default_factory=list,
        description="Node specific system instructions",
    )
    call_config: AIModelCallConfig = Field(
        default=None,
        description="Structured output model for the AI model response",
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
            if source_id not in available_node_ids and source_id != SpecialNodeIdEnum.PREVIOUS.value
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

    def get_system_instructions(self) -> str | None:
        """Returns the system instructions if set.

        Returns:
            str | None: Joined system instructions or None if not set
        """
        formatted = ""  # TODO
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
        options = self.call_config.options if self.call_config else {}

        if user_options is None:
            return options

        if options:
            merged = user_options.copy()
            merged.update(options)
            return merged

        return user_options
