from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
    TracingAttribute,
    common_tracing_attributes,
)

# Define all TracingAttribute variables

# Input attributes
base_directory_attr = TracingAttribute(
    name="base_directory",
    category="primary",
    display_name="Base Directory",
    description="Base directory for file operations",
    group_name="input",
    source_path="base_directory",
    data_type="string",
)

operations_count_attr = TracingAttribute(
    name="operations_count",
    category="primary",
    display_name="Operations Count",
    description="Number of operations to perform",
    group_name="input",
    source_path="operations",
    data_type="number",
    transform=lambda x: len(x) if x else 0,
)

# Output attributes
success_attr = TracingAttribute(
    name="success",
    category="primary",
    display_name="Success",
    description="Whether all operations were successful",
    group_name="output",
    source_path="data.success",
    data_type="boolean",
)

operations_count_attr = TracingAttribute(
    name="operations_count_output",
    category="primary",
    display_name="Operations Count",
    description="Number of operations performed",
    group_name="output",
    source_path="data.operations_count",
    data_type="number",
)

error_attr = TracingAttribute(
    name="error",
    category="primary",
    display_name="Error",
    description="Error message if operations failed",
    group_name="output",
    source_path="data.error",
    data_type="string",
)

# Result attributes
success_result_attr = TracingAttribute(
    name="success_result",
    category="primary",
    display_name="Success",
    description="Whether all operations were successful",
    group_name="result",
    source_path="outcome.success",
    data_type="boolean",
)

operations_count_attr = TracingAttribute(
    name="operations_count_result",
    category="primary",
    display_name="Total Operations",
    description="Total number of operations attempted",
    group_name="result",
    source_path="outcome.operations_count",
    data_type="number",
)

successful_operations_attr = TracingAttribute(
    name="successful_operations",
    category="primary",
    display_name="Successful Operations",
    description="Number of successful operations",
    group_name="result",
    source_path="outcome.successful_operations",
    data_type="number",
)

failed_operations_attr = TracingAttribute(
    name="failed_operations",
    category="primary",
    display_name="Failed Operations",
    description="Number of failed operations",
    group_name="result",
    source_path="outcome.failed_operations",
    data_type="number",
)

errors_result_attr = TracingAttribute(
    name="errors",
    category="primary",
    display_name="Errors",
    description="List of errors encountered",
    group_name="result",
    source_path="outcome.errors",
    data_type="array",
)

# Node internal attributes (from add_trace_attribute calls)
base_directory_attr = TracingAttribute(
    name="base_directory_internal",
    category="primary",
    display_name="Base Directory (Internal)",
    description="Base directory used during execution",
    group_name="node_internal",
    data_type="string",
)

operations_summary_attr = TracingAttribute(
    name="operations_summary",
    category="primary",
    display_name="Operations Summary",
    description="Summary of operations execution including total, successful, failed counts",
    group_name="node_internal",
    data_type="object",
)

operations_count_attr = TracingAttribute(
    name="operations_count_internal",
    category="primary",
    display_name="Operations Count (Internal)",
    description="Number of operations being executed",
    group_name="node_internal",
    data_type="number",
)

operations_results_attr = TracingAttribute(
    name="operations_results",
    category="primary",
    display_name="Operations Results",
    description="Detailed results of each operation execution",
    group_name="node_internal",
    data_type="array",
)

# Define File Operation Node tracing profile
file_operation_node_tracing_profile = NodeTracingProfile(
    node_type=FlowNodeTypeEnum.file_operation.value,
    tracing_attributes=[
        # Input attributes
        base_directory_attr,
        operations_count_attr,
        # Output attributes
        success_attr,
        operations_count_attr,
        error_attr,
        # Result attributes
        success_result_attr,
        operations_count_attr,
        successful_operations_attr,
        failed_operations_attr,
        errors_result_attr,
        # Node internal attributes
        base_directory_attr,
        operations_summary_attr,
        operations_count_attr,
        operations_results_attr,
        # Add common context attributes
        *common_tracing_attributes,
    ],
)
