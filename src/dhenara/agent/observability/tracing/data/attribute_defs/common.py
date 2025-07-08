from ..profile import TracingAttribute
from .execution_context_attributes import common_execution_context_attributes
from .fn_attributes import common_fn_trace_attributes
from .generic_attributes import common_generic_tracing_attributes

# Common tracing attributes that can be reused across nodes
common_tracing_attributes: list[TracingAttribute] = [
    *common_execution_context_attributes,
    *common_fn_trace_attributes,
    *common_generic_tracing_attributes,
]
