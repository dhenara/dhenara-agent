# dhenara/agent/dsl/inbuilt/flow_nodes/file_operation/tracing.py

from dhenara.agent.dsl.flow import FlowNodeTypeEnum
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
    TracingDataCategory,
    TracingDataField,
)

# Define File Operation Node tracing profile
file_operation_node_tracing_profile = NodeTracingProfile(
    node_type=FlowNodeTypeEnum.file_operation.value,
    # Primary input data
    input_fields=[
        TracingDataField(
            name="base_directory",
            source_path="base_directory",
            category=TracingDataCategory.primary,
            description="Base directory for file operations",
        ),
        TracingDataField(
            name="operations_count",
            source_path="operations",
            category=TracingDataCategory.primary,
            transform=lambda x: len(x) if x else 0,
            description="Number of operations to perform",
        ),
    ],
    # Primary output data
    output_fields=[
        TracingDataField(
            name="success",
            source_path="data.success",
            category=TracingDataCategory.primary,
            description="Whether all operations were successful",
        ),
        TracingDataField(
            name="operations_count",
            source_path="data.operations_count",
            category=TracingDataCategory.primary,
            description="Number of operations performed",
        ),
        TracingDataField(
            name="error",
            source_path="data.error",
            category=TracingDataCategory.primary,
            description="Error message if operations failed",
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
            description="Total number of operations attempted",
        ),
        TracingDataField(
            name="successful_operations",
            source_path="outcome.successful_operations",
            category=TracingDataCategory.primary,
            description="Number of successful operations",
        ),
        TracingDataField(
            name="failed_operations",
            source_path="outcome.failed_operations",
            category=TracingDataCategory.primary,
            description="Number of failed operations",
        ),
        TracingDataField(
            name="errors",
            source_path="outcome.errors",
            category=TracingDataCategory.primary,
            description="List of errors encountered",
        ),
    ],
)
