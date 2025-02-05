from typing import Any, NewType

from pydantic import Field, field_validator, model_validator

from dhenara.types.base import BaseModel
from dhenara.types.flow import (
    AISettings,
    ExecutionStrategyEnum,
    FlowNodePostActionEnum,
    FlowNodePreActionEnum,
    FlowNodeTypeEnum,
    NodeInputSettings,
    NodeResponseSettings,
    Resource,
    SpecialNodeIdEnum,
    StorageSettings,
    SystemInstructions,
)

''' TODO

class PromptOptionsSettings(BaseModel):
    """Configuration for an AI resource including prompts and options.

    This model defines the structure for configuring AI prompts and options.
    Either direct prompt or pre/post prompts can be used for constructing
    the final prompt sent to the AI model.

    Attributes:
        system_instructions: System-level instructions for the AI model as list of strings
        pre_prompt: Text to prepend to user prompt as list of strings
        prompt: Direct prompt text as list of strings
        post_prompt: Text to append to user prompt as list of strings
        options_overrides: Override options for AI model API calls
    """

    system_instructions: list[str] | None = Field(
        default=None,
        default_factory=None,
        description="System-level instructions provided to the AI model",
    )

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

    options_overrides: dict | None = Field(
        default=None,
        default_factory=None,
        description="Options to override default AI model API call parameters",
    )

    @model_validator(mode="after")
    def validate_prompt_configuration(self) -> "PromptOptionsSettings":
        """Validates that either prompt or pre/post prompt is provided."""
        if self.prompt and (self.pre_prompt or self.post_prompt):
            raise ValueError("Both 'prompt' and 'pre_prompt'/'post_prompt' are not allowed")
        # if not self.prompt and not (self.pre_prompt or self.post_prompt):
        #    raise ValueError("Either 'prompt' or 'pre_prompt'/'post_prompt' must be provided")
        return self

    def get_system_instructions(self) -> str | None:
        """Returns the system instructions if set.

        Returns:
            Optional[str]: Joined system instructions or None if not set
        """
        if self.system_instructions:
            return " ".join(self.system_instructions)
        return None

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

    def get_options(self, user_options: dict | None = None) -> dict:
        """Returns the merged options dictionary.

        Args:
            user_options: Optional user provided options to merge with overrides

        Returns:
            dict: Merged options with overrides taking precedence
        """
        if user_options is None:
            return self.options_overrides

        merged = user_options.copy()
        merged.update(self.options_overrides)
        return merged

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "system_instructions": ["You are a helpful assistant"],
                    "pre_prompt": ["Please answer the following question:"],
                    "post_prompt": ["Provide a detailed explanation."],
                    "options_overrides": {"temperature": 0.7},
                },
                {
                    "prompt": ["What is the capital of France?"],
                    "options_overrides": {"max_tokens": 100},
                },
            ]
        }
    }

'''

FlowNodeIdentifier = NewType("FlowNodeIdentifier", str)


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
    type: FlowNodeTypeEnum = Field(
        ...,
        description="Type of operation this node performs",
        examples=["ai_model_call", "rag_query"],
    )

    resources: list[Resource] | None = Field(
        default=None,
        description="List of resources to be used",
    )

    ai_settings: AISettings | None = Field(
        default=None,
        description="Node specific AP API settings/ options ",
    )
    input_settings: NodeInputSettings | None = Field(
        ...,
        description="Input Settings",
    )
    storage_settings: StorageSettings = Field(
        default_factory=dict,
        description="DataBase Storage settings",
    )
    response_settings: NodeResponseSettings = Field(
        ...,
        description="Response Settings",
    )
    pre_actions: list[FlowNodePreActionEnum] = Field(
        default_factory=list,
        description="Output actions",
    )
    post_actions: list[FlowNodePostActionEnum] = Field(
        default_factory=list,
        description="Output actions",
    )

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
    def validate_node_resources(cls, v: list[Resource]) -> list[Resource]:
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
                raise ValueError("One resource should be set as default")
            return v


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
    system_instructions: SystemInstructions | None = Field(
        default=None,
        description="Flow wide system instructions",
    )

    # node_prompt: NodePrompt | None = Field(
    #    default=None,
    #    description="Flow wide promts generation sinstruction/option parameters",
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
            node.input_settings.input_source.validate_node_references(list(all_node_identifies))

        return self


class Flow(BaseModel):
    """Model representing a complete flow."""

    name: str = Field(
        ...,
        description="Flow Name",
        min_length=5,
        max_length=200,
    )
    description: str | None = Field(
        ...,
        description="Optional description",
    )
    definition: FlowDefinition = Field(
        ...,
        description="Flow Definition",
    )
    is_active: bool = Field(
        default=True,
        description="Active or not",
    )
