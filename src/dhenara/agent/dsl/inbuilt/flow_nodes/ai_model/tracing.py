from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.observability.tracing import truncate_string
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
    TracingDataCategory,
    TracingDataField,
)


def truncate_prompt(prompt, max_length=500):
    """Truncate prompt text for display."""
    if not prompt:
        return None
    if hasattr(prompt, "text"):
        if isinstance(prompt.text, str):
            return truncate_string(prompt.text, max_length)
        elif hasattr(prompt.text, "text"):
            return truncate_string(prompt.text.text, max_length)
    return str(prompt)


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


# Define AI Model Node tracing profile
ai_model_node_tracing_profile = NodeTracingProfile(
    node_type=FlowNodeTypeEnum.ai_model_call.value,
    # Primary input data - what's being sent to the model
    input_fields=[
        TracingDataField(
            name="prompt_vars",
            source_path="prompt_variables",
            category=TracingDataCategory.primary,
            description="User prompt variables",
        ),
        TracingDataField(
            name="system_instructions_vars",
            source_path="instruction_variables",
            category=TracingDataCategory.primary,
            description="System instruction variables",
        ),
    ],
    # Primary output data - what's coming back from the model
    output_fields=[
        TracingDataField(
            name="response_text",
            source_path="data.response.chat_response.text()",
            category=TracingDataCategory.primary,
            max_length=1000,
            description="Model response text",
        ),
        TracingDataField(
            name="structured_output",
            source_path="data.response.chat_response.structured()",
            category=TracingDataCategory.primary,
            description="Structured output",
        ),
    ],
    # Result data - processed outcomes and metadata
    result_fields=[
        # Primary result data
        TracingDataField(
            name="response_text",
            source_path="outcome.text",
            category=TracingDataCategory.primary,
            max_length=1000,
            description="Response text",
        ),
        TracingDataField(
            name="has_structured_data",
            source_path="outcome.structured",
            category=TracingDataCategory.primary,
            transform=lambda x: bool(x),
            description="Has structured data",
        ),
        TracingDataField(
            name="token_usage",
            source_path="output.data.response.full_response.usage",
            category=TracingDataCategory.primary,
            transform=format_usage,
            description="Token usage",
        ),
        TracingDataField(
            name="token_usage",
            source_path="output.data.response.full_response.usage_charge",
            category=TracingDataCategory.primary,
            transform=format_usage_charge,
            description="Cost and Charges",
        ),
        TracingDataField(
            name="model",
            source_path="output.data.response.full_response.model",
            category=TracingDataCategory.primary,
            description="Model used",
        ),
        # Secondary result data
        TracingDataField(
            name="status",
            source_path="output.data.response.status",
            category=TracingDataCategory.secondary,
            description="Response status",
        ),
        TracingDataField(
            name="finish_reason",
            source_path="output.data.response.full_response.choices[0].finish_reason",
            category=TracingDataCategory.secondary,
            description="Finish reason",
        ),
        # Tertiary data (full details for debugging)
        TracingDataField(
            name="full_data",
            source_path="output.data",
            category=TracingDataCategory.tertiary,
            transform=lambda x: str(x)[:1000] if x else None,
            description="Complete output data",
        ),
    ],
    ## Context data - execution environment
    # context_fields=[
    #    TracingDataField(
    #        name="flow_id", source_path="component_id", category=TracingDataCategory.secondary, description="Flow ID"
    #    ),
    # ],
)
