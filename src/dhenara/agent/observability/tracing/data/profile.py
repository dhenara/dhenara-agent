from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TracingDataCategory(Enum):
    """Categories for organizing tracing data by importance."""

    primary = "primary"  # Most important data, shown first/highlighted
    secondary = "secondary"  # Supporting data, shown on hover/expand
    tertiary = "tertiary"  # Technical details, only shown on detailed view


@dataclass
class TracingDataField:
    """Definition of a field to be captured for tracing."""

    name: str  # Name used in the trace data
    source_path: str  # Path to extract data from (dot notation)
    category: TracingDataCategory  # Importance category
    transform: Callable | None = None  # Optional transformation function
    max_length: int | None = None  # Max length for string values (for truncation)
    description: str | None = None  # Human-readable description


common_context_fields = [
    # Primary context fields - most important execution information
    # TracingDataField(
    #    name="context_id",
    #    source_path="context_id",
    #    category=TracingDataCategory.primary,
    #    description="Unique identifier for this execution",
    # ),
    TracingDataField(
        name="hierarchy_path",
        source_path="hierarchy_path",
        category=TracingDataCategory.primary,
        description="hierarchy_path of the context",
    ),
    TracingDataField(
        name="start_hierarchy_path",
        source_path="start_hierarchy_path",
        category=TracingDataCategory.primary,
        description="start_hierarchy_path from the run context",
    ),
    TracingDataField(
        name="execution_status",
        source_path="execution_status",
        category=TracingDataCategory.primary,
        description="Status of the execution (pending, complete, failed)",
    ),
    # Secondary context fields - supporting execution information
    TracingDataField(
        name="created_at",
        source_path="created_at",
        category=TracingDataCategory.secondary,
        transform=lambda x: x.isoformat() if x else None,
        description="When this execution started",
    ),
    TracingDataField(
        name="completed_at",
        source_path="completed_at",
        category=TracingDataCategory.secondary,
        transform=lambda x: x.isoformat() if x else None,
        description="When this execution completed",
    ),
    TracingDataField(
        name="execution_type",
        source_path="executable_type",
        category=TracingDataCategory.secondary,
        description="Type of execution (flow, node, agent)",
    ),
    # Tertiary context fields - technical details
    TracingDataField(
        name="error_message",
        source_path="execution_failed_message",
        category=TracingDataCategory.tertiary,
        description="Error message if execution failed",
    ),
    TracingDataField(
        name="parent_context",
        source_path="parent.component_id",
        category=TracingDataCategory.tertiary,
        transform=lambda x: x.component_id if x else "No-parent",
        description="Parent execution context ID, if any",
    ),
    # TracingDataField(
    #    name="resource_config",
    #    source_path="resource_config",
    #    category=TracingDataCategory.tertiary,
    #    transform=lambda x: x.model_dump() if hasattr(x, "model_dump") else str(x),
    #    description="Resource configuration for this execution",
    # ),
    TracingDataField(
        name="metadata",
        source_path="metadata",
        category=TracingDataCategory.tertiary,
        transform=lambda x: {k: v for k, v in x.items() if isinstance(v, (str, int, float, bool))} if x else {},
        description="Additional execution metadata",
        max_length=500,
    ),
]


@dataclass
class NodeTracingProfile:
    """Defines how a node's execution should be traced."""

    node_type: str = "unknown_node"  # Type of node this profile applies to
    input_fields: list[TracingDataField] = field(default_factory=list)  # Fields to capture from input
    output_fields: list[TracingDataField] = field(default_factory=list)  # Fields to capture from output
    result_fields: list[TracingDataField] = field(default_factory=list)  # Fields to capture from result
    context_fields: list[TracingDataField] = field(
        default_factory=lambda: list(common_context_fields)
    )  # Fields from execution context

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary for storage/reference."""
        return {
            "node_type": self.node_type,
            "input_fields": [vars(f) for f in self.input_fields],
            "output_fields": [vars(f) for f in self.output_fields],
            "result_fields": [vars(f) for f in self.result_fields],
            "context_fields": [vars(f) for f in self.context_fields],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NodeTracingProfile":
        """Create profile from dictionary."""
        profile = cls(node_type=data["node_type"])

        for field_type in ["input_fields", "output_fields", "result_fields", "context_fields"]:
            if field_type in data:
                setattr(
                    profile,
                    field_type,
                    [
                        TracingDataField(
                            name=f["name"],
                            source_path=f["source_path"],
                            category=TracingDataCategory(f["category"]),
                            transform=f.get("transform"),
                            max_length=f.get("max_length"),
                            description=f.get("description"),
                        )
                        for f in data[field_type]
                    ],
                )

        return profile


@dataclass
class ComponentTracingProfile(NodeTracingProfile):
    component_type: str = "unknown_component"
