from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
    TracingAttribute,
    common_tracing_attributes,
)


def format_usage(usage):
    """Format token usage information."""
    if not usage:
        return None

    result = {}
    if hasattr(usage, "prompt_tokens"):
        result["prompt_tokens"] = usage.prompt_tokens
    if hasattr(usage, "completion_tokens"):
        result["completion_tokens"] = usage.completion_tokens
    if hasattr(usage, "total_tokens"):
        result["total_tokens"] = usage.total_tokens
    if hasattr(usage, "estimated_cost"):
        result["cost"] = f"${usage.estimated_cost:.6f}" if usage.estimated_cost else "N/A"

    return result


def format_usage_charge(usage_charge):
    """Format token usage information."""
    if not usage_charge:
        return None

    result = {}
    if hasattr(usage_charge, "cost"):
        result["cost"] = f"${usage_charge.cost:.6f}" if usage_charge.cost else "N/A"
    if hasattr(usage_charge, "charge"):
        result["charge"] = f"${usage_charge.charge:.6f}" if usage_charge.charge else "N/A"

    return result


# Tracing attributes
# Input attributes
prompt_vars_attr = TracingAttribute(
    name="prompt_vars",
    category="primary",
    display_name="Prompt Variables",
    description="User prompt variables",
    group_name="input",
    source_path="prompt_variables",
    data_type="object",
    collapsible=True,
)

system_instructions_vars_attr = TracingAttribute(
    name="system_instructions_vars",
    category="primary",
    display_name="System Instructions Variables",
    description="System instruction variables",
    group_name="input",
    source_path="instruction_variables",
    data_type="object",
    collapsible=True,
)

# Output attributes
response_text_output_attr = TracingAttribute(
    name="response_text",
    category="primary",
    display_name="Response Text",
    description="Model response text",
    group_name="output",
    source_path="data.response.chat_response.text()",
    data_type="string",
    max_length=1000,
)

structured_output_attr = TracingAttribute(
    name="structured_output",
    category="primary",
    display_name="Structured Output",
    description="Structured output",
    group_name="output",
    source_path="data.response.chat_response.structured()",
    data_type="object",
    collapsible=True,
)

# Result attributes
response_text_result_attr = TracingAttribute(
    name="response_text",
    category="primary",
    display_name="Response Text",
    description="Response text",
    group_name="result",
    source_path="outcome.text",
    data_type="string",
    max_length=1000,
)

has_structured_data_attr = TracingAttribute(
    name="has_structured_data",
    category="primary",
    display_name="Has Structured Data",
    description="Has structured data",
    group_name="result",
    source_path="outcome.structured",
    data_type="boolean",
    transform=lambda x: bool(x),
)

token_usage_attr = TracingAttribute(
    name="token_usage",
    category="primary",
    display_name="Token Usage",
    description="Token usage",
    group_name="result",
    source_path="output.data.response.full_response.usage",
    data_type="object",
    transform=format_usage,
    format_hint="usage_stats",
    icon="tokens",
)

token_cost_attr = TracingAttribute(
    name="token_cost",
    category="primary",
    display_name="Cost and Charges",
    description="Cost and Charges",
    group_name="result",
    source_path="output.data.response.full_response.usage_charge",
    data_type="object",
    transform=format_usage_charge,
    format_hint="currency",
    icon="dollar",
)

model_attr = TracingAttribute(
    name="model",
    category="primary",
    display_name="Model Used",
    description="Model used",
    group_name="result",
    source_path="output.data.response.full_response.model",
    data_type="string",
    icon="model",
)

status_attr = TracingAttribute(
    name="status",
    category="secondary",
    display_name="Response Status",
    description="Response status",
    group_name="result",
    source_path="output.data.response.status",
    data_type="string",
)

finish_reason_attr = TracingAttribute(
    name="finish_reason",
    category="secondary",
    display_name="Finish Reason",
    description="Finish reason",
    group_name="result",
    source_path="output.data.response.full_response.choices[0].finish_reason",
    data_type="string",
)

full_data_attr = TracingAttribute(
    name="full_data",
    category="tertiary",
    display_name="Full Output Data",
    description="Complete output data",
    group_name="result",
    source_path="output.data",
    data_type="object",
    transform=lambda x: str(x)[:1000] if x else None,
    collapsible=True,
)

# Node internal attributes (from add_trace_attribute calls)
node_resource_type_attr = TracingAttribute(
    name="node_resource_type",
    category="secondary",
    display_name="Node Resource Type",
    description="Type of resource used by the node",
    group_name="node_internal",
    data_type="string",
)

node_resource_query_attr = TracingAttribute(
    name="node_resource_query",
    category="secondary",
    display_name="Node Resource Query",
    description="Query associated with the node resource",
    group_name="node_internal",
    data_type="string",
)

ai_model_name_attr = TracingAttribute(
    name="ai_model_name",
    category="primary",
    display_name="AI Model Name",
    description="Name of the AI model used",
    group_name="node_internal",
    data_type="string",
)

ai_model_provider_attr = TracingAttribute(
    name="ai_model_provider",
    category="primary",
    display_name="AI Model Provider",
    description="Provider of the AI model",
    group_name="node_internal",
    data_type="string",
)

ai_model_api_provider_attr = TracingAttribute(
    name="ai_model_api_provider",
    category="primary",
    display_name="AI Model API Provider",
    description="API provider for the AI model",
    group_name="node_internal",
    data_type="string",
)

final_prompt_attr = TracingAttribute(
    name="final_prompt",
    category="primary",
    display_name="Final Prompt",
    description="Final rendered prompt sent to the model",
    group_name="node_internal",
    data_type="string",
    max_length=1000,
)

system_instructions_attr = TracingAttribute(
    name="system_instructions",
    category="primary",
    display_name="System Instructions",
    description="System instructions used in the call",
    group_name="node_internal",
    data_type="array",
)

context_count_attr = TracingAttribute(
    name="context_count",
    category="primary",
    display_name="Context Count",
    description="Number of context items provided",
    group_name="node_internal",
    data_type="number",
)

prompt_context_0_attr = TracingAttribute(
    name="prompt_context_0",
    category="secondary",
    display_name="Prompt Context Item 0",
    description="First Prompt context item preview",
    group_name="node_internal",
    data_type="string",
    max_length=500,
)

prompt_context_1_attr = TracingAttribute(
    name="prompt_context_1",
    category="secondary",
    display_name="Prompt Context Item 1",
    description="Second Prompt context item preview",
    group_name="node_internal",
    data_type="string",
    max_length=500,
)

prompt_context_2_attr = TracingAttribute(
    name="prompt_context_2",
    category="secondary",
    display_name="Prompt Context Item 2",
    description="Third Prompt context item preview",
    group_name="node_internal",
    data_type="string",
    max_length=500,
)

model_options_attr = TracingAttribute(
    name="model_options",
    category="primary",
    display_name="Model Options",
    description="Options passed to the model",
    group_name="node_internal",
    data_type="object",
)

test_mode_attr = TracingAttribute(
    name="test_mode",
    category="primary",
    display_name="Test Mode",
    description="Whether test mode is enabled",
    group_name="node_internal",
    data_type="boolean",
)

model_call_config_attr = TracingAttribute(
    name="model_call_config",
    category="secondary",
    display_name="Model Call Config",
    description="Configuration for the model call",
    group_name="node_internal",
    data_type="object",
)

api_call_started_attr = TracingAttribute(
    name="api_call_started",
    category="primary",
    display_name="API Call Started",
    description="Timestamp when API call was initiated",
    group_name="node_internal",
    data_type="string",
    format_hint="datetime",
)

cost_attr = TracingAttribute(
    name="cost",
    category="primary",
    display_name="Cost",
    description="Cost of the API call",
    group_name="node_internal",
    data_type="string",
    format_hint="currency",
)

charge_attr = TracingAttribute(
    name="charge",
    category="primary",
    display_name="Charge",
    description="Charge for the API call",
    group_name="node_internal",
    data_type="string",
    format_hint="currency",
)

# Define AI Model Node tracing profile
ai_model_node_tracing_profile = NodeTracingProfile(
    node_type=FlowNodeTypeEnum.ai_model_call.value,
    tracing_attributes=[
        # Input attributes
        prompt_vars_attr,
        system_instructions_vars_attr,
        # Output attributes
        response_text_output_attr,
        structured_output_attr,
        # Result attributes
        response_text_result_attr,
        has_structured_data_attr,
        token_usage_attr,
        token_cost_attr,
        model_attr,
        status_attr,
        finish_reason_attr,
        full_data_attr,
        # Node internal attributes
        node_resource_type_attr,
        node_resource_query_attr,
        ai_model_name_attr,
        ai_model_provider_attr,
        ai_model_api_provider_attr,
        final_prompt_attr,
        system_instructions_attr,
        context_count_attr,
        prompt_context_0_attr,
        prompt_context_1_attr,
        prompt_context_2_attr,
        model_options_attr,
        test_mode_attr,
        model_call_config_attr,
        api_call_started_attr,
        cost_attr,
        charge_attr,
        # Add common context attributes
        *common_tracing_attributes,
    ],
)
