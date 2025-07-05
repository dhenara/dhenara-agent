from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TracingAttribute:
    """Definition of a tracing attribute with display metadata."""

    name: str  # The attribute name
    category: Literal["primary", "secondary", "tertiary"]  # Importance category
    data_type: Literal["string", "number", "boolean", "object", "array"] = "string"

    # Display metadata for frontend
    display_name: str = ""  # Human-readable name for UI
    description: str = ""  # Description

    # Processing options
    node_field_type: Literal[
        "input",
        "output",
        "result",
        "execution_context",
        "node_internal",
        "not_applicable",
    ] = "not_applicable"
    source_path: str = ""  # Path to extract data from (dot notation)
    transform: Callable | None = None  # Optional transformation function
    max_length: int | None = None  # Max length for string values

    # UI display options
    format_hint: str | None = None  # UI formatting hint (e.g., "currency", "duration", "bytes")
    icon: str | None = None  # Optional icon identifier for UI
    collapsible: bool = False  # Whether this attribute can be collapsed in detailed view

    def __post_init__(self):
        # Set display_name to name if not provided
        if not self.display_name:
            self.display_name = self.name.replace("_", " ").title()


@dataclass
class NodeTracingProfile:
    node_type: str = "unknown_node"  # Type of node this profile applies to
    tracing_attributes: list[TracingAttribute] = field(
        default_factory=list
    )  # List of attributes in the preferred order of display in FE

    @property
    def input_fields(self) -> list[TracingAttribute]:
        """Get attributes that are extracted from input."""
        return [attr for attr in self.tracing_attributes if attr.node_field_type == "input"]

    @property
    def output_fields(self) -> list[TracingAttribute]:
        """Get attributes that are extracted from output."""
        return [attr for attr in self.tracing_attributes if attr.node_field_type == "output"]

    @property
    def result_fields(self) -> list[TracingAttribute]:
        """Get attributes that are extracted from result."""
        return [attr for attr in self.tracing_attributes if attr.node_field_type == "result"]

    @property
    def context_fields(self) -> list[TracingAttribute]:
        """Get attributes that are extracted from execution context."""
        return [attr for attr in self.tracing_attributes if attr.node_field_type == "execution_context"]

    '''
    TODO: Delete
    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary for storage/reference."""
        return {
            "node_type": self.node_type,
            "tracing_attributes": [
                {
                    "name": attr.name,
                    "category": attr.category,
                    "data_type": attr.data_type,
                    "display_name": attr.display_name,
                    "description": attr.description,
                    "node_field_type": attr.node_field_type,
                    "source_path": attr.source_path,
                    "max_length": attr.max_length,
                    "format_hint": attr.format_hint,
                    "icon": attr.icon,
                    "collapsible": attr.collapsible,
                }
                for attr in self.tracing_attributes
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NodeTracingProfile":
        """Create profile from dictionary."""
        attributes = []
        for attr_data in data.get("tracing_attributes", []):
            attributes.append(
                TracingAttribute(
                    name=attr_data["name"],
                    category=attr_data["category"],
                    data_type=attr_data.get("data_type", "string"),
                    display_name=attr_data.get("display_name", ""),
                    description=attr_data.get("description", ""),
                    node_field_type=attr_data.get("node_field_type", "internal"),
                    source_path=attr_data.get("source_path", ""),
                    max_length=attr_data.get("max_length"),
                    format_hint=attr_data.get("format_hint"),
                    icon=attr_data.get("icon"),
                    collapsible=attr_data.get("collapsible", False),
                )
            )

        return cls(
            node_type=data.get("node_type", "unknown_node"),
            tracing_attributes=attributes,
        )
     '''


# Common context attributes that can be reused across nodes
common_context_attributes = [
    TracingAttribute(
        name="hierarchy_path",
        category="primary",
        display_name="Hierarchy Path",
        description="Hierarchy path of the context",
        node_field_type="execution_context",
        source_path="hierarchy_path",
    ),
    TracingAttribute(
        name="start_hierarchy_path",
        category="primary",
        display_name="Start Hierarchy Path",
        description="Start hierarchy path from the run context",
        node_field_type="execution_context",
        source_path="start_hierarchy_path",
    ),
    TracingAttribute(
        name="execution_status",
        category="primary",
        display_name="Execution Status",
        description="Status of the execution (pending, complete, failed)",
        node_field_type="execution_context",
        source_path="execution_status",
    ),
    TracingAttribute(
        name="created_at",
        category="secondary",
        display_name="Created At",
        description="When this execution started",
        node_field_type="execution_context",
        source_path="created_at",
        transform=lambda x: x.isoformat() if x else None,
        format_hint="datetime",
    ),
    TracingAttribute(
        name="completed_at",
        category="secondary",
        display_name="Completed At",
        description="When this execution completed",
        node_field_type="execution_context",
        source_path="completed_at",
        transform=lambda x: x.isoformat() if x else None,
        format_hint="datetime",
    ),
    TracingAttribute(
        name="execution_type",
        category="secondary",
        display_name="Execution Type",
        description="Type of execution (flow, node, agent)",
        node_field_type="execution_context",
        source_path="executable_type",
    ),
    TracingAttribute(
        name="error_message",
        category="tertiary",
        display_name="Error Message",
        description="Error message if execution failed",
        node_field_type="execution_context",
        source_path="execution_failed_message",
    ),
    TracingAttribute(
        name="parent_context",
        category="tertiary",
        display_name="Parent Context",
        description="Parent execution context ID, if any",
        node_field_type="execution_context",
        source_path="parent.component_id",
        transform=lambda x: x.component_id if x else "No-parent",
    ),
    TracingAttribute(
        name="metadata",
        category="tertiary",
        display_name="Metadata",
        description="Additional execution metadata",
        node_field_type="execution_context",
        source_path="metadata",
        transform=lambda x: {k: v for k, v in x.items() if isinstance(v, (str, int, float, bool))} if x else {},
        max_length=500,
        collapsible=True,
    ),
]


@dataclass
class ComponentTracingProfile(NodeTracingProfile):
    component_type: str = "unknown_component"
