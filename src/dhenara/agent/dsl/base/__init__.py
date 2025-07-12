# Base Element

from .enums import (
    SpecialNodeIDEnum,
    ComponentTypeEnum,
    ExecutionStatusEnum,
    ExecutionStrategyEnum,
    ExecutableTypeEnum,
    ControlBlockTypeEnum,
)
from .defs import NodeID
from .fns import ensure_object_template, auto_converr_str_to_template, is_string_hier_or_expr
from .data.template_engine import TemplateEngine
from .data.dad_template_engine import DADTemplateEngine

from .node.node_settings import (
    NodeSettings,
    RecordFileFormatEnum,
    RecordSettingsItem,
    NodeRecordSettings,
)
from .node.node_io import NodeInput, NodeInputs, NodeOutput, NodeOutcome, NodeOutcomeT, NodeInputT, NodeOutputT
from .node.node_exe_result import NodeExecutionResult


# Executable Elements
from .context import ExecutionContext, StreamingContext, StreamingStatusEnum, ContextT
# Do not imprt ExecutionContextRegistry in the package, use it directly in run_ctx
# from .contex_registry import ExecutionContextRegistry

from .executable import Executable
from .node.node_def import ExecutableNodeDefinition, NodeDefT
from .node.node_executor import NodeExecutor
from .node.node import ExecutableNode, NodeT

# Component
from .component.component_io import ComponentInput, ComponentInputT
from .component.comp_exe_result import ComponentExecutionResult, ComponentExeResultT
from .component.component_def import ComponentDefinition, ComponentDefT
from .component.control import Conditional, ForEach
from .component.executor import ComponentExecutor
from .component.component import ExecutableComponent, ComponentT

import warnings
from dhenara.agent.types import PLACEHOLDER as _PLACEHOLDER, PlaceholderType as _PlaceholderType


class DeprecatedPlaceholder(_PlaceholderType):
    def __new__(cls, *args, **kwargs):
        warnings.warn(
            "PLACEHOLDER and PlaceholderType are deprecated in this module. "
            "Please import them directly from dhenara.agent.types",
            DeprecationWarning,
            stacklevel=2,
        )
        return super().__new__(cls, *args, **kwargs)


PLACEHOLDER = _PLACEHOLDER
PlaceholderType = DeprecatedPlaceholder


__all__ = [
    "ComponentDefT",
    "ComponentDefinition",
    "ComponentExeResultT",
    "ComponentExecutionResult",
    "ComponentExecutor",
    "ComponentInput",
    "ComponentInputT",
    "ComponentT",
    "ComponentTypeEnum",
    "Conditional",
    "ContextT",
    "ControlBlockTypeEnum",
    "DADTemplateEngine",
    "Executable",
    "ExecutableComponent",
    "ExecutableNode",
    "ExecutableNodeDefinition",
    "ExecutableTypeEnum",
    "ExecutionContext",
    "ExecutionStatusEnum",
    "ExecutionStrategyEnum",
    "ForEach",
    "NodeDefT",
    "NodeExecutionResult",
    "NodeExecutor",
    "NodeID",
    "NodeID",
    "NodeInput",
    "NodeInputT",
    "NodeInputs",
    "NodeOutcome",
    "NodeOutcomeT",
    "NodeOutput",
    "NodeOutputT",
    "NodeRecordSettings",
    "NodeSettings",
    "NodeT",
    "RecordFileFormatEnum",
    "RecordSettingsItem",
    "SpecialNodeIDEnum",
    "StreamingContext",
    "StreamingStatusEnum",
    "TemplateEngine",
    "auto_converr_str_to_template",
    "ensure_object_template",
    "is_string_hier_or_expr",
]
