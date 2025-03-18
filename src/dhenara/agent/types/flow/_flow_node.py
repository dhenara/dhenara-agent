
from pydantic import Field, field_validator, model_validator

from dhenara.agent.types.flow import (
    AISettings,
    CommandSettings,
    FlowNodeIdentifier,
    FlowNodeInput,
    FlowNodeTypeEnum,
    FolderAnalyzerSettings,
    GitRepoAnalyzerSettings,
    NodeInputSettings,
    NodeResponseSettings,
)
from dhenara.ai.types import ResourceConfigItem
from dhenara.ai.types.shared.base import BaseModel


class FlowNode(BaseModel):
    """Model representing a single node in the flow.

    A node defines an operational unit within a flow, containing its execution
    parameters, configuration

    Attributes:
        identifier: Unique identifier for the node
        type: Operation type this node performs
        order: Execution sequence number
        config: FlowNode-specific configuration parameters
    """

    order: int = Field(
        ...,
        description="Execution sequence number",
        ge=0,
        examples=[1],
    )

    identifier: FlowNodeIdentifier = Field(
        ...,
        description="Unique human readable identifier for the node",
        min_length=1,
        max_length=150,
        pattern="^[a-zA-Z0-9_-]+$",
        examples=["initial_model_call", "context_retrieval", "final_summary"],
    )
    info: str | None = Field(
        default=None,
        description=("General purpose string. Can be user to show a message to the user while executing this node"),
    )

    type: FlowNodeTypeEnum = Field(
        ...,
        description="Type of operation this node performs",
        examples=["ai_model_call", "rag_query"],
    )

    resources: list[ResourceConfigItem] = Field(
        default_factory=list,
        description="List of resources to be used",
    )
    tools: list = Field(
        default_factory=list,
        description="Tools",
    )
    command_settings: CommandSettings | None = Field(
        default=None,
        description="Settings for command execution nodes",
    )
    folder_analyzer_settings: FolderAnalyzerSettings | None = Field(
        default=None, description="Settings for folder analyzer nodes"
    )

    git_repo_analyzer_settings: GitRepoAnalyzerSettings | None = Field(
        default=None, description="Settings for git repository analyzer nodes"
    )

    ai_settings: AISettings | None = Field(
        default=None,
        description="Node specific AP API settings/ options ",
    )
    input_settings: NodeInputSettings | None = Field(
        default=None,
        description="Input Settings",
    )
    # storage_settings: StorageSettings = Field(
    #    default_factory=dict,
    #    description="DataBase Storage settings",
    # )
    response_settings: NodeResponseSettings | None = Field(
        default=None,
        description="Response Settings",
    )

    # pre_actions: list[FlowNodePreActionEnum] = Field(
    #    default_factory=list,
    #    description="Output actions",
    # )
    # post_actions: list[FlowNodePostActionEnum] = Field(
    #    default_factory=list,
    #    description="Output actions",
    # )

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate node identifier format.

        Args:
            v: The identifier string to validate

        Returns:
            The validated identifier string

        Raises:
            ValueError: If identifier is empty or contains only whitespace
        """
        if not v.strip():
            raise ValueError("FlowNode identifier cannot be empty or whitespace")
        return v

    @field_validator("resources")
    @classmethod
    def validate_node_resources(
        cls,
        v: list[ResourceConfigItem],
    ) -> list[ResourceConfigItem]:
        """Validate that node IDs are unique within the same flow level."""
        # Ignore empty lists
        if not v:
            return v

        default_count = sum(1 for resource in v if resource.is_default)
        if default_count > 1:
            raise ValueError("Only one resource can be set as default")

        # If there is only one resource, set it as default and return
        if len(v) == 1:
            v[0].is_default = True
            return v
        else:
            if default_count < 1:
                raise ValueError("resources: One resource should be set as default")
            return v

    @model_validator(mode="after")
    def validate_node_type_settings(self) -> "FlowNode":
        """Validate that settings match the node type."""
        if self.type == FlowNodeTypeEnum.command and self.command_settings is None:
            raise ValueError("command_settings must be provided for nodes of type 'command'")

        if self.type == FlowNodeTypeEnum.folder_analyzer and self.folder_analyzer_settings is None:
            raise ValueError("folder_analyzer_settings must be provided for nodes of type 'folder_analyzer'")

        if self.type == FlowNodeTypeEnum.git_repo_analyzer and self.git_repo_analyzer_settings is None:
            raise ValueError("git_repo_analyzer_settings must be provided for nodes of type 'git_repo_analyzer'")

        if self.type in [FlowNodeTypeEnum.ai_model_call, FlowNodeTypeEnum.ai_model_call_stream] and (
            self.ai_settings is None or self.input_settings is None
        ):
            raise ValueError("ai_settings & input_settings  must be provided for nodes of type 'ai_model_call*'")

        return self

    # @model_validator(mode="after")
    # def validate_input_settings(self) -> "FlowNode":
    #    """Validates that input settings and AI settings are not conflicting.
    #
    #    This validator ensures that user input sources and node prompts are not
    #    configured simultaneously, which would create ambiguous input handling.
    #
    #    Returns:
    #        Self instance if validation passes
    #    Raises:
    #        ValueError: If conflicting settings are detected
    #    """
    #    has_prompt = self.ai_settings and self.ai_settings.node_prompt.format() and self.ai_settings.node_prompt.prompt
    #    has_user_input = self.input_settings and self.input_settings.input_source and self.input_settings.input_source.user_input_sources  # noqa: E501, W505
    #    if has_prompt and has_user_input:
    #        raise ValueError(
    #            "Illegal input settings configuration: "
    #            "`input_source.user_input_sources` and `ai_settings.node_prompt.prompt` "
    #            "cannot be set simultaneously. To modify user inputs for this node, "
    #            "use the `pre` and `post` fields of `node_prompt`, not the `prompt` field.",
    #        )
    #    return self

    async def get_full_input_content(self, node_input: FlowNodeInput, **kwargs) -> str:
        node_prompt = self.ai_settings.node_prompt if self.ai_settings and self.ai_settings.node_prompt else None
        input_content = node_input.content.get_content() if node_input and node_input.content else None

        if node_prompt:
            if input_content is None:
                input_content = ""  # An empty string is better that the word None

            kwargs.update({"dh_input_content": input_content})

            return node_prompt.format(**kwargs)

        else:
            if not input_content:
                raise ValueError(
                    f"Illegal Node setting for node {self.identifier}:  node_prompt and input_content are empty"
                )

            return input_content

    def is_streaming(self):
        return self.type in [FlowNodeTypeEnum.ai_model_call_stream]

    def check_resource_in_node(self, resource: ResourceConfigItem) -> bool:
        """
        Checks if a given resource exists in the node's resource list.

        Args:
            resource: ResourceConfigItem object to check for

        Returns:
            bool: True if the resource exists in the node's resources, False otherwise
        """
        if not self.resources:
            return False

        return any(existing_resource.is_same_as(resource) for existing_resource in self.resources)
