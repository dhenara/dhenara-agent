from pydantic import Field, field_validator, model_validator

from dhenara.agent.dsl.base import NodeSettings, SpecialNodeIDEnum
from dhenara.ai.types.genai.dhenara import (
    AIModelCallConfig,
    Prompt,
    SystemInstruction,
    TextTemplate,
)
from dhenara.ai.types.resource import ResourceConfigItem


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
    models: list[str] | None = Field(
        default=None,
        description="List of model names. This is a shortcut to add models to `resources` ",
    )
    resources: list[ResourceConfigItem] | None = Field(
        default=None,
        description="List of resources to be used",
    )
    # Additional setting to store images
    save_generated_bytes: bool = Field(
        default=True,
        description="Whether to save generated (image) bytes into files. Applicable only for Image generation",
    )
    bytes_save_path: str | TextTemplate | None = Field(
        default="$var{element_hier_path}/",
        description="Path to save the generated (image) files. Default is set to node hierarchy path inside run dir",
    )
    bytes_save_filename_prefix: str | TextTemplate | None = Field(
        default="auto",
        description=(
            "File name prefix for generated (image) files. "
            "Timestamp and a signature will be appended after this. "
            "If multiple files are generated, the file names will end with an `_<index>`."
        ),
    )

    @field_validator("resources")
    @classmethod
    def validate_node_resources(
        cls,
        v: list[ResourceConfigItem],
    ) -> list[ResourceConfigItem]:
        # Ignore empty lists
        if not v:
            return v

        default_count = sum(1 for resource in v if resource.is_default)
        if default_count > 1:
            raise ValueError(f"Only one resource can be set as default. resource={v}")

        # If there is only one resource, set it as default and return
        if len(v) == 1:
            v[0].is_default = True
            return v
        else:
            if default_count < 1:
                raise ValueError("resources: One resource should be set as default")
            return v

    @model_validator(mode="before")
    @classmethod
    def validate_models(cls, data):
        if isinstance(data, dict):
            models = data.get("models")

            if models:
                data["resources"] = ResourceConfigItem.with_models(models)

        return data

    @field_validator("context_sources")
    @classmethod
    def validate_source_ids(cls, source_ids: list[str]) -> list[str]:
        """Validate that source IDs are non-empty strings."""
        if any(not source_id.strip() for source_id in source_ids):
            raise ValueError("Source IDs must be non-empty strings")
        return [source_id.strip() for source_id in source_ids]
