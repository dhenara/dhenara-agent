from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
    TracingAttribute,
    common_tracing_attributes,
)

# Input attributes
base_directory_input_attr = TracingAttribute(
    name="base_directory",
    category="primary",
    display_name="Base Directory",
    description="Base directory for operations",
    group_name="input",
    source_path="base_directory",
    data_type="string",
)

operations_count_input_attr = TracingAttribute(
    name="operations_count",
    category="primary",
    display_name="Operations Count",
    description="Number of operations to perform",
    group_name="input",
    source_path="operations",
    data_type="number",
    transform=lambda x: len(x) if x else 0,
)

exclude_patterns_input_attr = TracingAttribute(
    name="exclude_patterns",
    category="secondary",
    display_name="Exclude Patterns",
    description="Patterns to exclude",
    group_name="input",
    source_path="exclude_patterns",
    data_type="array",
)

# Output attributes
success_output_attr = TracingAttribute(
    name="success",
    category="primary",
    display_name="Success",
    description="Whether analysis was successful",
    group_name="output",
    source_path="data.success",
    data_type="boolean",
)

base_directory_output_attr = TracingAttribute(
    name="base_directory",
    category="primary",
    display_name="Base Directory",
    description="Base directory for operations",
    group_name="output",
    source_path="data.base_directory",
    data_type="string",
)

operations_count_output_attr = TracingAttribute(
    name="operations_count",
    category="primary",
    display_name="Operations Count",
    description="Number of operations performed",
    group_name="output",
    source_path="data.operations_count",
    data_type="number",
)

successful_operations_output_attr = TracingAttribute(
    name="successful_operations",
    category="primary",
    display_name="Successful Operations",
    description="Number of successful operations",
    group_name="output",
    source_path="data.successful_operations",
    data_type="number",
)

failed_operations_output_attr = TracingAttribute(
    name="failed_operations",
    category="primary",
    display_name="Failed Operations",
    description="Number of failed operations",
    group_name="output",
    source_path="data.failed_operations",
    data_type="number",
)

errors_output_attr = TracingAttribute(
    name="errors",
    category="primary",
    display_name="Errors",
    description="List of errors encountered",
    group_name="output",
    source_path="data.errors",
    data_type="array",
)

# Result attributes
success_result_attr = TracingAttribute(
    name="success",
    category="primary",
    display_name="Success",
    description="Whether all operations were successful",
    group_name="result",
    source_path="outcome.success",
    data_type="boolean",
)

operations_count_result_attr = TracingAttribute(
    name="operations_count",
    category="primary",
    display_name="Total Operations",
    description="Total number of operations performed",
    group_name="result",
    source_path="outcome.operations_count",
    data_type="number",
)

total_files_result_attr = TracingAttribute(
    name="total_files",
    category="primary",
    display_name="Total Files",
    description="Total number of files found",
    group_name="result",
    source_path="outcome.total_files",
    data_type="number",
)

total_directories_result_attr = TracingAttribute(
    name="total_directories",
    category="primary",
    display_name="Total Directories",
    description="Total number of directories found",
    group_name="result",
    source_path="outcome.total_directories",
    data_type="number",
)

total_size_result_attr = TracingAttribute(
    name="total_size",
    category="primary",
    display_name="Total Size",
    description="Total size in bytes",
    group_name="result",
    source_path="outcome.total_size",
    data_type="number",
    format_hint="bytes",
)

file_types_result_attr = TracingAttribute(
    name="file_types",
    category="secondary",
    display_name="File Types",
    description="Count of files by extension",
    group_name="result",
    source_path="outcome.file_types",
    data_type="object",
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
    name="base_directory",
    category="tertiary",
    display_name="Base Directory Internal",
    description="Base directory resolved during execution",
    group_name="node_internal",
    data_type="string",
)

operations_summary_attr = TracingAttribute(
    name="operations_summary",
    category="tertiary",
    display_name="Operations Summary",
    description="Summary of operations execution status",
    group_name="node_internal",
    data_type="object",
)

operations_count_attr = TracingAttribute(
    name="operations_count",
    category="tertiary",
    display_name="Operations Count Internal",
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


# Define Folder Analyzer Node tracing profile
folder_analyzer_node_tracing_profile = NodeTracingProfile(
    node_type=FlowNodeTypeEnum.folder_analyzer.value,
    tracing_attributes=[
        # Input attributes
        base_directory_input_attr,
        operations_count_input_attr,
        exclude_patterns_input_attr,
        # Output attributes
        success_output_attr,
        base_directory_output_attr,
        operations_count_output_attr,
        successful_operations_output_attr,
        failed_operations_output_attr,
        errors_output_attr,
        # Result attributes
        success_result_attr,
        operations_count_result_attr,
        total_files_result_attr,
        total_directories_result_attr,
        total_size_result_attr,
        file_types_result_attr,
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
