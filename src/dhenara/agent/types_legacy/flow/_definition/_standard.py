from typing import Any, ClassVar

from pydantic import Field, field_validator, model_validator

from dhenara.agent.types.flow import (
    BaseFlow,
    ExecutionStrategyEnum,
    FlowTypeEnum,
    LegacyFlowNode,
    ResponseProtocolEnum,
    SpecialNodeIdEnum,
)


class StandardFlow(BaseFlow):
    """Standard flow definition with nodes."""

    flow_type: ClassVar[FlowTypeEnum | None] = FlowTypeEnum.standard

    execution_strategy: ExecutionStrategyEnum = Field(
        ...,
        description="Execution strategy for top-level nodes",
        examples=["sequential"],
    )

    nodes: list[LegacyFlowNode] = Field(
        ...,
        description="List of nodes in execution order",
        min_items=1,
    )

    def _collect_all_identifiers(self, node: LegacyFlowNode, identifiers: set[str]) -> None:
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
    def validate_node_order(cls, v: list[LegacyFlowNode]) -> list[LegacyFlowNode]:
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
        #    raise ValueError("LegacyFlowNode orders must be unique")
        # if sorted(orders) != list(range(min(orders), max(orders) + 1)):
        #    raise ValueError("LegacyFlowNode orders must be sequential")
        # return v

        expected_orders = list(range(len(v)))
        if orders != expected_orders:
            raise ValueError(
                "LegacyFlowNode orders must be sequential starting from 0 within each flow",
            )
        return v

    @field_validator("nodes")
    @classmethod
    def validate_node_identifiers(cls, v: list[LegacyFlowNode]) -> list[LegacyFlowNode]:
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
            raise ValueError("LegacyFlowNode IDs must be unique within the same flow level")

        for node_id in ids:
            if node_id in SpecialNodeIdEnum.values():
                raise ValueError(f"LegacyFlowNode IDs `{v}` is a reserved identifier")

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
            ...     LegacyFlowNode(identifier="node1", ...),
            ...     LegacyFlowNode(identifier="node2", ...),
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
