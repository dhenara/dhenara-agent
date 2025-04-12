from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
    TracingDataCategory,
    TracingDataField,
)

# Define Folder Analyzer Node tracing profile
# Modify folder_analyzer/tracing.py
folder_analyzer_node_tracing_profile = NodeTracingProfile(
    node_type=FlowNodeTypeEnum.folder_analyzer.value,
    # Primary input data
    input_fields=[
        TracingDataField(
            name="base_directory",
            source_path="base_directory",
            category=TracingDataCategory.primary,
            description="Base directory for operations",
        ),
        TracingDataField(
            name="operations_count",
            source_path="operations",
            category=TracingDataCategory.primary,
            transform=lambda x: len(x) if x else 0,
            description="Number of operations to perform",
        ),
        TracingDataField(
            name="exclude_patterns",
            source_path="exclude_patterns",
            category=TracingDataCategory.secondary,
            description="Patterns to exclude",
        ),
    ],
    # Primary output data
    output_fields=[
        TracingDataField(
            name="success",
            source_path="data.success",
            category=TracingDataCategory.primary,
            description="Whether analysis was successful",
        ),
        TracingDataField(
            name="base_directory",
            source_path="data.base_directory",
            category=TracingDataCategory.primary,
            description="Base directory for operations",
        ),
        TracingDataField(
            name="operations_count",
            source_path="data.operations_count",
            category=TracingDataCategory.primary,
            description="Number of operations performed",
        ),
        TracingDataField(
            name="successful_operations",
            source_path="data.successful_operations",
            category=TracingDataCategory.primary,
            description="Number of successful operations",
        ),
        TracingDataField(
            name="failed_operations",
            source_path="data.failed_operations",
            category=TracingDataCategory.primary,
            description="Number of failed operations",
        ),
        TracingDataField(
            name="errors",
            source_path="data.errors",
            category=TracingDataCategory.primary,
            description="List of errors encountered",
        ),
    ],
    # Result data
    result_fields=[
        TracingDataField(
            name="success",
            source_path="outcome.success",
            category=TracingDataCategory.primary,
            description="Whether all operations were successful",
        ),
        TracingDataField(
            name="operations_count",
            source_path="outcome.operations_count",
            category=TracingDataCategory.primary,
            description="Total number of operations performed",
        ),
        TracingDataField(
            name="total_files",
            source_path="outcome.total_files",
            category=TracingDataCategory.primary,
            description="Total number of files found",
        ),
        TracingDataField(
            name="total_directories",
            source_path="outcome.total_directories",
            category=TracingDataCategory.primary,
            description="Total number of directories found",
        ),
        TracingDataField(
            name="total_size",
            source_path="outcome.total_size",
            category=TracingDataCategory.primary,
            description="Total size in bytes",
        ),
        TracingDataField(
            name="file_types",
            source_path="outcome.file_types",
            category=TracingDataCategory.secondary,
            description="Count of files by extension",
        ),
        TracingDataField(
            name="errors",
            source_path="outcome.errors",
            category=TracingDataCategory.primary,
            description="List of errors encountered",
        ),
    ],
)
