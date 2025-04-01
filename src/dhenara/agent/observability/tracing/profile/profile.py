# dhenara/agent/observability/tracing/profile.py
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TracingDataCategory(Enum):
    """Categories for organizing tracing data by importance."""

    PRIMARY = "primary"  # Most important data, shown first/highlighted
    SECONDARY = "secondary"  # Supporting data, shown on hover/expand
    TERTIARY = "tertiary"  # Technical details, only shown on detailed view


@dataclass
class TracingDataField:
    """Definition of a field to be captured for tracing."""

    name: str  # Name used in the trace data
    source_path: str  # Path to extract data from (dot notation)
    category: TracingDataCategory  # Importance category
    transform: Callable | None = None  # Optional transformation function
    max_length: int | None = None  # Max length for string values (for truncation)
    description: str | None = None  # Human-readable description


@dataclass
class NodeTracingProfile:
    """Defines how a node's execution should be traced."""

    node_type: str  # Type of node this profile applies to
    input_fields: list[TracingDataField] = field(default_factory=list)  # Fields to capture from input
    output_fields: list[TracingDataField] = field(default_factory=list)  # Fields to capture from output
    result_fields: list[TracingDataField] = field(default_factory=list)  # Fields to capture from result
    context_fields: list[TracingDataField] = field(default_factory=list)  # Fields from execution context

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


# Registry to store tracing profiles for different node types
class TracingProfileRegistry:
    """Registry for node tracing profiles."""

    _profiles: dict[str, NodeTracingProfile] = {}

    @classmethod
    def register(cls, profile: NodeTracingProfile) -> None:
        """Register a tracing profile for a node type."""
        cls._profiles[profile.node_type] = profile

    @classmethod
    def get(cls, node_type: str) -> NodeTracingProfile | None:
        """Get a tracing profile for a node type."""
        return cls._profiles.get(node_type)

    @classmethod
    def get_or_default(cls, node_type: str) -> NodeTracingProfile:
        """Get a tracing profile for a node type or a default profile."""
        if node_type in cls._profiles:
            return cls._profiles[node_type]
        return NodeTracingProfile(node_type=node_type)
