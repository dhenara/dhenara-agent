from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
    TracingDataCategory,
    TracingDataField,
)

# Define Folder Analyzer Node tracing profile
folder_analyzer_node_tracing_profile = NodeTracingProfile(
    node_type=FlowNodeTypeEnum.folder_analyzer.value,
    # Primary input data
    input_fields=[
        TracingDataField(
            name="path",
            source_path="path",
            category=TracingDataCategory.primary,
            description="Path to analyze",
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
            name="path",
            source_path="data.path",
            category=TracingDataCategory.primary,
            description="Path analyzed",
        ),
        TracingDataField(
            name="error",
            source_path="data.error",
            category=TracingDataCategory.primary,
            description="Error message if analysis failed",
        ),
    ],
    # Result data
    result_fields=[
        TracingDataField(
            name="success",
            source_path="outcome.success",
            category=TracingDataCategory.primary,
            description="Whether analysis was successful",
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
