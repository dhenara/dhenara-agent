from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TracingAttribute:
    """Definition of a tracing attribute with display metadata."""

    name: str  # The attribute name
    group_name: Literal[
        # Nodes & Components
        "input",
        "output",
        "result",
        "execution_context",
        "node_internal",
        # Others
        "fn_trace",
        "trace_debug",
        "generic",
        "custom",
    ]
    data_type: Literal["string", "number", "boolean", "object", "array"]
    category: Literal["primary", "secondary", "tertiary"] = "primary"  # Importance category
    # Display metadata for frontend
    display_name: str = ""  # Human-readable name for UI
    description: str = ""  # Description

    # Processing options
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
class TracingProfileBase:
    tracing_attributes: list[TracingAttribute] = field(
        default_factory=list
    )  # List of attributes in the preferred order of display in FE

    @property
    def input_fields(self) -> list[TracingAttribute]:
        """Get attributes that are extracted from input."""
        return [attr for attr in self.tracing_attributes if attr.group_name == "input"]

    @property
    def output_fields(self) -> list[TracingAttribute]:
        """Get attributes that are extracted from output."""
        return [attr for attr in self.tracing_attributes if attr.group_name == "output"]

    @property
    def result_fields(self) -> list[TracingAttribute]:
        """Get attributes that are extracted from result."""
        return [attr for attr in self.tracing_attributes if attr.group_name == "result"]

    @property
    def context_fields(self) -> list[TracingAttribute]:
        """Get attributes that are extracted from execution context."""
        return [attr for attr in self.tracing_attributes if attr.group_name == "execution_context"]


@dataclass
class NodeTracingProfile(TracingProfileBase):
    node_type: str = "unknown_node"


@dataclass
class ComponentTracingProfile(TracingProfileBase):
    component_type: str = "unknown_component"
