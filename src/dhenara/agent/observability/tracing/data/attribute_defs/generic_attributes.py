from ..profile import TracingAttribute

node_id_attr = TracingAttribute(
    name="node_id",
    category="primary",
    group_name="generic",
    data_type="string",
    display_name="Node ID",
    description="Unique identifier for the node",
)

node_type_attr = TracingAttribute(
    name="node_type",
    category="primary",
    group_name="generic",
    data_type="string",
    display_name="Node Type",
    description="Type of the node being executed",
)

node_hierarchy_attr = TracingAttribute(
    name="node_hierarchy",
    category="secondary",
    group_name="generic",
    data_type="string",
    display_name="Node Hierarchy",
    description="Hierarchical path of the node",
)

component_id_attr = TracingAttribute(
    name="component_id",
    category="primary",
    group_name="generic",
    data_type="string",
    display_name="Component ID",
    description="Unique identifier for the component",
)

component_type_attr = TracingAttribute(
    name="component_type",
    category="primary",
    group_name="generic",
    data_type="string",
    display_name="Component Type",
    description="Type of the component being executed",
)

component_hierarchy_attr = TracingAttribute(
    name="component_hierarchy",
    category="secondary",
    group_name="generic",
    data_type="string",
    display_name="Component Hierarchy",
    description="Hierarchical path of the component",
)

execution_start_time_attr = TracingAttribute(
    name="execution_start_time",
    category="secondary",
    group_name="generic",
    data_type="number",
    display_name="Start Time",
    description="Execution start timestamp",
    format_hint="timestamp",
)

execution_end_time_attr = TracingAttribute(
    name="execution_end_time",
    category="secondary",
    group_name="generic",
    data_type="number",
    display_name="End Time",
    description="Execution end timestamp",
    format_hint="timestamp",
)

execution_duration_attr = TracingAttribute(
    name="execution_duration_ms",
    category="primary",
    group_name="generic",
    data_type="number",
    display_name="Duration (ms)",
    description="Execution duration in milliseconds",
    format_hint="duration",
)

execution_status_attr = TracingAttribute(
    name="execution_status",
    category="primary",
    group_name="generic",
    data_type="string",
    display_name="Status",
    description="Execution status (success/error)",
)


parent_trace_id_attr = TracingAttribute(
    name="parent_trace_id",
    category="tertiary",
    group_name="trace_debug",
    data_type="string",
    display_name="Parent Trace ID",
    description="Trace ID of the parent span",
)

parent_span_id_attr = TracingAttribute(
    name="parent_span_id",
    category="tertiary",
    group_name="trace_debug",
    data_type="string",
    display_name="Parent Span ID",
    description="Span ID of the parent span",
)

error_type_attr = TracingAttribute(
    name="error_type",
    category="primary",
    group_name="generic",
    data_type="string",
    display_name="Error Type",
    description="Type of error that occurred",
)

error_message_attr = TracingAttribute(
    name="error_message",
    category="primary",
    group_name="generic",
    data_type="string",
    display_name="Error Message",
    description="Error message details",
    max_length=1000,
)

# Trace debugs
trace_errors_attr = TracingAttribute(
    name="trace_errors",
    category="primary",
    group_name="trace_debug",
    data_type="string",
    display_name="Trace Errors ",
    description="Errors in Tracing",
)
trace_warnings_attr = TracingAttribute(
    name="trace_warnings",
    category="primary",
    group_name="trace_debug",
    data_type="string",
    display_name="Trace Warnings ",
    description="Warnings in Tracing",
)
trace_infos_attr = TracingAttribute(
    name="trace_infos",
    category="secondary",
    group_name="trace_debug",
    data_type="string",
    display_name="Trace Infos ",
    description="Info Messages in Tracing",
)
trace_debugs_attr = TracingAttribute(
    name="trace_debugs",
    category="tertiary",
    group_name="trace_debug",
    data_type="string",
    display_name="Trace debugs ",
    description="Debug Messages in Tracing",
)


common_generic_tracing_attributes: list[TracingAttribute] = [
    node_id_attr,
    node_type_attr,
    node_hierarchy_attr,
    component_id_attr,
    component_type_attr,
    component_hierarchy_attr,
    execution_start_time_attr,
    execution_end_time_attr,
    execution_duration_attr,
    execution_status_attr,
    parent_trace_id_attr,
    parent_span_id_attr,
    error_type_attr,
    error_message_attr,
    # Trace Debugs
    trace_errors_attr,
    trace_warnings_attr,
    trace_infos_attr,
    trace_debugs_attr,
]
