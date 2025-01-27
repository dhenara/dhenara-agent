from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from ..base import BaseModel
from .flow_data import Resource


class ExecutionStrategyEnum(str, Enum):
    """Enum defining execution strategy for flow nodes.

    Attributes:
        sequential: Nodes execute one after another in sequence
        parallel: Nodes execute simultaneously in parallel
    """

    sequential = "sequential"
    parallel = "parallel"


class NodeTypeEnum(str, Enum):
    """Enum defining types of flow nodes.

    Attributes:
        ai_model_sync: Synchronous AI model inference
        ai_model_stream: AI model inference with streaming
        ai_model_async: Asynchronous AI model inference
        rag_index: RAG index creation operation
        rag_query: RAG query/retrieval operation
        stream: Generic streaming operation
    """

    ai_model_sync = "ai_model_sync"
    ai_model_stream = "ai_model_stream"
    ai_model_async = "ai_model_async"
    rag_index = "rag_index"
    rag_query = "rag_query"
    stream = "stream"


class Node(BaseModel):
    """Model representing a single node in the flow.

    A node defines an operational unit within a flow, containing its execution
    parameters, configuration, and optional subflow.

    Attributes:
        identifier: Unique identifier for the node
        type: Operation type this node performs
        order: Execution sequence number
        config: Node-specific configuration parameters
        subflow: Optional nested flow for complex operations
    """

    identifier: str = Field(
        ...,
        description="Unique human readable identifier for the node",
        min_length=1,
        max_length=150,
        pattern="^[a-zA-Z0-9_-]+$",
        examples=["initial_model_call", "context_retrieval", "final_summary"],
    )
    type: NodeTypeEnum = Field(
        ...,
        description="Type of operation this node performs",
        examples=["ai_model_sync", "rag_query"],
    )
    order: int = Field(
        ...,
        description="Execution sequence number",
        ge=0,
        examples=[1],
    )
    config: dict[str, Any] = Field(
        ...,
        description="Node-specific configuration parameters",
        examples=[{"model_name": "gpt-4", "temperature": 0.7}],
    )
    resources: list[Resource] = Field(
        ...,
        description="List of resources to be used",
    )
    subflow: "FlowDefinition | None" = Field(
        default=None,
        description="Optional nested flow definition for complex operations",
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
            raise ValueError("Node identifier cannot be empty or whitespace")
        return v

    @field_validator("config")
    @classmethod
    def validate_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate that config is not empty.

        Args:
            v: The config dictionary to validate

        Returns:
            The validated config dictionary

        Raises:
            ValueError: If config is empty
        """
        if not v:
            raise ValueError("Config cannot be empty")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "identifier": "initial_model_call",
                    "type": "ai_model_sync",
                    "order": 1,
                    "config": {
                        "model_name": "gpt-4",
                        "temperature": 0.7,
                    },
                    "subflow": {
                        "nodes": [
                            {
                                "identifier": "preprocessing",
                                "type": "stream",
                                "order": 0,
                                "config": {"filter": "text"},
                            },
                        ],
                        "execution_strategy": "sequential",
                    },
                },
            ],
        },
    }


class FlowDefinition(BaseModel):
    """Model representing a complete flow definition.

    A flow orchestrates multiple nodes in a specific order and execution strategy,
    defining the overall processing pipeline.

    Attributes:
        nodes: List of nodes comprising the flow
        execution_strategy: Strategy for executing top-level nodes
    """

    nodes: list[Node] = Field(
        ...,
        description="List of nodes in execution order",
        min_items=1,
    )
    execution_strategy: ExecutionStrategyEnum = Field(
        ...,
        description="Execution strategy for top-level nodes",
        examples=["sequential"],
    )

    def _collect_all_identifiers(self, node: Node, identifiers: set[str]) -> None:
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
    def validate_node_order(cls, v: list[Node]) -> list[Node]:
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
        #    raise ValueError("Node orders must be unique")
        # if sorted(orders) != list(range(min(orders), max(orders) + 1)):
        #    raise ValueError("Node orders must be sequential")
        # return v

        expected_orders = list(range(len(v)))
        if orders != expected_orders:
            raise ValueError(
                "Node orders must be sequential starting from 0 within each flow",
            )
        return v

    @field_validator("nodes")
    @classmethod
    def validate_node_identifiers(cls, v: list[Node]) -> list[Node]:
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
            raise ValueError("Node IDs must be unique within the same flow level")
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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "nodes": [
                        {
                            "identifier": "create_index",
                            "type": "rag_index",
                            "order": 0,
                            "config": {"index_name": "docs"},
                            "subflow": {
                                "nodes": [
                                    {
                                        "identifier": "process_documents",
                                        "type": "stream",
                                        "order": 0,
                                        "config": {"chunk_size": 1000},
                                    },
                                ],
                                "execution_strategy": "sequential",
                            },
                        },
                        {
                            "identifier": "generate_summary",
                            "type": "ai_model_sync",
                            "order": 1,
                            "config": {"model_name": "gpt-4"},
                        },
                    ],
                    "execution_strategy": "sequential",
                },
            ],
        },
    }
