# dhenara/agent/dsl/inbuilt/flow_nodes/command/tracing.py

from dhenara.agent.dsl.flow import FlowNodeTypeEnum
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
    TracingDataCategory,
    TracingDataField,
)

# Define Command Node tracing profile
command_node_tracing_profile = NodeTracingProfile(
    node_type=FlowNodeTypeEnum.command.value,
    # Primary input data - what's being sent to command execution
    input_fields=[
        TracingDataField(
            name="env_vars",
            source_path="env_vars",
            category=TracingDataCategory.secondary,
            description="Environment variables for command execution",
        ),
        TracingDataField(
            name="commands",
            source_path="commands",
            category=TracingDataCategory.primary,
            description="Commands to execute",
        ),
    ],
    # Primary output data - what's coming back from command execution
    output_fields=[
        TracingDataField(
            name="all_succeeded",
            source_path="data.all_succeeded",
            category=TracingDataCategory.primary,
            description="Whether all commands succeeded",
        ),
        TracingDataField(
            name="results_count",
            source_path="data.results",
            category=TracingDataCategory.secondary,
            transform=lambda x: len(x) if x else 0,
            description="Number of command results",
        ),
    ],
    # Result data - processed outcomes and metadata
    result_fields=[
        TracingDataField(
            name="all_succeeded",
            source_path="outcome.all_succeeded",
            category=TracingDataCategory.primary,
            description="Whether all commands succeeded",
        ),
        TracingDataField(
            name="commands_executed",
            source_path="outcome.commands_executed",
            category=TracingDataCategory.primary,
            description="Number of commands executed",
        ),
        TracingDataField(
            name="successful_commands",
            source_path="outcome.successful_commands",
            category=TracingDataCategory.primary,
            description="Number of successful commands",
        ),
        TracingDataField(
            name="failed_commands",
            source_path="outcome.failed_commands",
            category=TracingDataCategory.primary,
            description="Number of failed commands",
        ),
    ],
)
