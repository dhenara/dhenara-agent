from dhenara.agent.types.base import BaseEnum


class ExecutableTypeEnum(BaseEnum):
    flow_node = "flow_node"
    flow = "flow"
    agent = "agent"


class ControlBlockTypeEnum(BaseEnum):
    conditional = "conditional"
    foreach = "foreach"


# Enum for component type to be used in tracing and logging, similar to NodeTypeEnum. This is purely for tracing.
class ComponentTypeEnum(BaseEnum):
    flow = "flow"
    agent = "agent"


# INFO: NodeTypeEnum will be defined per component type
# class NodeTypeEnum(BaseEnum):
#    pass


class SpecialNodeIDEnum(BaseEnum):
    """Special node identifiers for input sources."""

    PREVIOUS = "previous"  # Reference to previous node


class ExecutionStatusEnum(BaseEnum):
    """Generic execution status enum that can be used by any DSL component."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionStrategyEnum(BaseEnum):
    """Enum defining execution strategy for flow nodes.

    Attributes:
        sequential: FlowNodes execute one after another in sequence
        parallel: FlowNodes execute simultaneously in parallel
    """

    sequential = "sequential"
    parallel = "parallel"


# class FlowTypeEnum(BaseEnum):
#    standard = "standard"
#    condition = "condition"  # If-else branching
#    loop = "loop"  # Iteration
#    switch = "switch"  # Multiple branching
#    # custom = "custom"
