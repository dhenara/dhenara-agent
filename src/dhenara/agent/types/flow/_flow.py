from typing import Any

from pydantic import Field, field_validator, model_validator

from dhenara.agent.types.flow import (
    AISettings,
    CommandSettings,
    ExecutionStrategyEnum,
    FlowNodeIdentifier,
    FlowNodeInput,
    FlowNodeTypeEnum,
    FolderAnalyzerSettings,
    GitRepoAnalyzerSettings,
    NodeInputSettings,
    NodeResponseSettings,
    ResponseProtocolEnum,
    SpecialNodeIdEnum,
    SystemInstructions,
)
from dhenara.ai.types import ResourceConfigItem
from dhenara.ai.types.shared.base import BaseModel


class FlowNode(BaseModel):
    """Model representing a single node in the flow.

    A node defines an operational unit within a flow, containing its execution
    parameters, configuration, and optional subflow.

    Attributes:
        identifier: Unique identifier for the node
        type: Operation type this node performs
        order: Execution sequence number
        config: FlowNode-specific configuration parameters
        subflow: Optional nested flow for complex operations
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

    subflow: "FlowDefinition | None" = Field(
        default=None,
        description="Optional nested flow definition for complex operations",
        default_factory=None,
        exclude=True,  # NOTE: as this is factory, base model exclude won't work
    )

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


class FlowDefinition(BaseModel):
    """Model representing a complete flow definition.

    A flow orchestrates multiple nodes in a specific order and execution strategy,
    defining the overall processing pipeline.

    Attributes:
        nodes: List of nodes comprising the flow
        execution_strategy: Strategy for executing top-level nodes
    """

    nodes: list[FlowNode] = Field(
        ...,
        description="List of nodes in execution order",
        min_items=1,
    )
    execution_strategy: ExecutionStrategyEnum = Field(
        ...,
        description="Execution strategy for top-level nodes",
        examples=["sequential"],
    )
    response_protocol: ResponseProtocolEnum = Field(
        ...,
        description="Response protocol for all nodes in the flow. Individual nodes can enalbe/disable responses",
    )
    system_instructions: SystemInstructions | None = Field(
        default=None,
        description="Flow wide system instructions",
    )

    # node_prompt: PromptTemplate | None = Field(
    #    default=None,
    #    description="Flow wide prompts generation sinstruction/option parameters",
    # )

    # ai_settings: AISettings | None = Field(
    #    default=None,
    #    description="Flow wide AP API settings/ options ",
    # )

    def _collect_all_identifiers(self, node: FlowNode, identifiers: set[str]) -> None:
        """Recursively collect all node identifiers including subflows.

        Args:
            node: Current node to process
            identifiers: Set to store all identifiers

        Raises:
            ValueError: If duplicate identifier is found
        """
        if node.identifier in identifiers:
            raise ValueError(f"Duplicate node identifier found: {node.identifier}")
        identifiers.add(node.identifier)

        if node.subflow:
            for subnode in node.subflow.nodes:
                self._collect_all_identifiers(subnode, identifiers)

    @field_validator("nodes")
    @classmethod
    def validate_node_order(cls, v: list[FlowNode]) -> list[FlowNode]:
        """Validate that node orders are sequential within the flow.

        Args:
            v: List of nodes to validate

        Returns:
            The validated list of nodes

        Raises:
            ValueError: If node orders are not sequential starting from 0
        """
        orders = [node.order for node in v]
        # if len(orders) != len(set(orders)):
        #    raise ValueError("FlowNode orders must be unique")
        # if sorted(orders) != list(range(min(orders), max(orders) + 1)):
        #    raise ValueError("FlowNode orders must be sequential")
        # return v

        expected_orders = list(range(len(v)))
        if orders != expected_orders:
            raise ValueError(
                "FlowNode orders must be sequential starting from 0 within each flow",
            )
        return v

    @field_validator("nodes")
    @classmethod
    def validate_node_identifiers(cls, v: list[FlowNode]) -> list[FlowNode]:
        """Validate that node IDs are unique within the same flow level.

        Args:
            v: List of nodes to validate

        Returns:
            The validated list of nodes

        Raises:
            ValueError: If node IDs are not unique
        """
        ids = [node.identifier for node in v]
        if len(ids) != len(set(ids)):
            raise ValueError("FlowNode IDs must be unique within the same flow level")

        for node_id in ids:
            if node_id in SpecialNodeIdEnum.values():
                raise ValueError(f"FlowNode IDs `{v}` is a reserved identifier")

        return v

    def validate_all_identifiers(self) -> None:
        """Validate uniqueness of all node identifiers across the entire flow.

        Raises:
            ValueError: If any duplicate identifiers are found
        """
        all_identifiers: set[str] = set()
        for node in self.nodes:
            self._collect_all_identifiers(node, all_identifiers)

    def model_post_init(self, __context: Any) -> None:
        """Perform post-initialization validation.

        Args:
            __context: Context object passed by Pydantic

        Raises:
            ValueError: If validation fails
        """
        self.validate_all_identifiers()

    @model_validator(mode="after")
    def validate_node_identifies(self):
        all_node_identifies = {node.identifier for node in self.nodes}
        for node in self.nodes:
            if node.input_settings:
                node.input_settings.validate_node_references(list(all_node_identifies))

        return self

    def has_any_streaming_node(self) -> bool:
        """Check if any flow_node in the flow requires streaming"""
        return any(flow_node.is_streaming() for flow_node in self.nodes)

    @model_validator(mode="after")
    def validate_response_protocol(self):
        if self.has_any_streaming_node():
            if self.response_protocol not in [ResponseProtocolEnum.HTTP_SSE]:
                raise ValueError("Response protocol must be one that support streaming if any node is streaming.")
        return self

    def get_previous_node_identifier(self, node_identifier: str) -> str | None:
        """Returns the identifier of the node that precedes the specified node.

        This method performs various sanity checks to ensure the node exists and
        has a valid previous node in the sequence.

        Args:
            node_identifier: The identifier of the current node

        Returns:
            Optional[str]: The identifier of the previous node, or None if:
                - The specified node is the first node in the flow
                - The specified node doesn't exist in the flow

        Raises:
            ValueError: If the provided node_identifier is empty or invalid

        Examples:
            >>> flow = FlowDefinition(nodes=[
            ...     FlowNode(identifier="node1", ...),
            ...     FlowNode(identifier="node2", ...),
            ... ])
            >>> flow.get_previous_node_identifier("node2")
            'node1'
            >>> flow.get_previous_node_identifier("node1")
            None
        """
        if not node_identifier:
            raise ValueError("Node identifier cannot be empty")

        # Create a list of node identifiers
        node_ids = [node.identifier for node in self.nodes]

        try:
            # Find the index of the current node
            current_index = node_ids.index(node_identifier)

            # Return None if it's the first node
            if current_index == 0:
                return None

            # Return the previous node's identifier
            return node_ids[current_index - 1]

        except ValueError:
            # Node identifier not found in the flow
            return None
