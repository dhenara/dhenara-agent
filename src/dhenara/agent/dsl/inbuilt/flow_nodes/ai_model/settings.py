# TODO: Move sertting from legacy

from pydantic import Field, field_validator

from dhenara.agent.dsl.base import NodeSettings, SpecialNodeIDEnum
from dhenara.ai.types.genai.dhenara import AIModelCallConfig, Prompt, SystemInstruction


class AIModelNodeSettings(NodeSettings):
    """Configuration for AI model options and settings.

    This model defines the structure for configuring AI model options and settings.
    """

    prompt: Prompt | None = Field(
        default=None,
        description="Node specific prompts generation sinstruction/option parameters",
    )
    context: list[Prompt] | None = Field(
        default=None,
        description="Context for ai model all",
    )
    context_sources: list[str] | None = Field(
        default=None,
        description=(
            f"List of node IDs or special identifiers to collect node output from. "
            "Note that this will be passed as context to the current node model call"
            f"Use '{SpecialNodeIDEnum.PREVIOUS}' for previous node output"
        ),
        example=["previous", "node_1", "node_2"],
    )
    system_instructions: list[str | SystemInstruction] | None = Field(
        default=None,
        description="Node specific system instructions",
    )
    model_call_config: AIModelCallConfig | None = Field(
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
        #    if source_id not in available_node_ids and source_id != SpecialNodeIDEnum.FULL.value
        # }
        # if invalid_contents:
        #    raise ValueError(
        #        f"Invalid user input source IDs: {', '.join(invalid_contents)}",
        #    )

        # Validate node output sources
        invalid_node_outputs = {
            source_id
            for source_id in self.context_sources
            if source_id not in available_node_ids and source_id != SpecialNodeIDEnum.PREVIOUS.value
        }
        if invalid_node_outputs:
            raise ValueError(
                f"Invalid node output source IDs: {', '.join(invalid_node_outputs)}",
            )

        return True

    # TODO: delete this fn
    @property
    def uses_previous_node(self) -> bool:
        """Check if the node uses output from the previous node."""
        return SpecialNodeIDEnum.PREVIOUS.value in self.context_sources
