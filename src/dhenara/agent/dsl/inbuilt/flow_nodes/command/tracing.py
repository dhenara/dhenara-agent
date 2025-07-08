from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
    TracingAttribute,
    common_tracing_attributes,
)

# Input attributes
env_vars_attr = TracingAttribute(
    name="env_vars",
    category="secondary",
    display_name="Environment Variables",
    description="Environment variables for command execution",
    group_name="input",
    source_path="env_vars",
    data_type="object",
    collapsible=True,
    icon="environment",
)
input_command_attr = TracingAttribute(
    name="commands",
    category="primary",
    display_name="Commands",
    description="Commands to execute",
    group_name="input",
    source_path="commands",
    data_type="array",
    icon="terminal",
)
# Output attributes
data_all_succeeded_attr = TracingAttribute(
    name="all_succeeded",
    category="primary",
    display_name="All Commands Succeeded",
    description="Whether all commands succeeded",
    group_name="output",
    source_path="data.all_succeeded",
    data_type="boolean",
    icon="check",
)
results_count_attr = TracingAttribute(
    name="results_count",
    category="secondary",
    display_name="Results Count",
    description="Number of command results",
    group_name="output",
    source_path="data.results",
    data_type="number",
    transform=lambda x: len(x) if x else 0,
    icon="count",
)
# Result attributes
all_succeeded_attr = TracingAttribute(
    name="all_succeeded",
    category="primary",
    display_name="All Commands Succeeded",
    description="Whether all commands succeeded",
    group_name="result",
    source_path="outcome.all_succeeded",
    data_type="boolean",
    icon="check",
)
commands_executed_attr = TracingAttribute(
    name="commands_executed",
    category="primary",
    display_name="Commands Executed",
    description="Number of commands executed",
    group_name="result",
    source_path="outcome.commands_executed",
    data_type="number",
    icon="play",
)
successful_commands_attr = TracingAttribute(
    name="successful_commands",
    category="primary",
    display_name="Successful Commands",
    description="Number of successful commands",
    group_name="result",
    source_path="outcome.successful_commands",
    data_type="number",
    icon="check-circle",
)
failed_commands_attr = TracingAttribute(
    name="failed_commands",
    category="primary",
    display_name="Failed Commands",
    description="Number of failed commands",
    group_name="result",
    source_path="outcome.failed_commands",
    data_type="number",
    icon="x-circle",
)

# Internal attributes
commands_data_attr = TracingAttribute(
    name="commands_data",
    category="primary",
    display_name="Commands Data",
    description="Commands Data",
    group_name="node_internal",
    data_type="object",
    icon="data",
)
commands_summary_attr = TracingAttribute(
    name="commands_summary",
    category="primary",
    display_name="Commands summary",
    description="Commands summar",
    group_name="node_internal",
    data_type="object",
    icon="data",
)

command_node_tracing_profile = NodeTracingProfile(
    node_type=FlowNodeTypeEnum.command.value,
    tracing_attributes=[
        env_vars_attr,
        input_command_attr,
        data_all_succeeded_attr,
        results_count_attr,
        all_succeeded_attr,
        commands_executed_attr,
        successful_commands_attr,
        failed_commands_attr,
        # Add common context attributes
        *common_tracing_attributes,
    ],
)
