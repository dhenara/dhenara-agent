from dhenara.agent.types import (
    Agent,
    AISettings,
    ExecutionStrategyEnum,
    FlowDefinition,
    FlowNode,
    FlowNodeTypeEnum,
    NodeInputSettings,
    NodeResponseSettings,
    PromptTemplate,
    ResponseProtocolEnum,
    SpecialNodeIdEnum,
)
from dhenara.ai.types import (
    AIModelAPIProviderEnum,
    ResourceConfigItem,
    ResourceConfigItemTypeEnum,
    ResourceQueryFieldsEnum,
)

# NOTE: `agent_identifier` is used for naming run dirs.
# Its OK to change during bringup, but be aware of the run dir naminig dependency
agent_identifier = "{{agent_identifier}}"


# Agent definition,  modify as per your need
# NOTE: The instance name should be `agent_definition`
agent_definition = Agent(
    identifier=agent_identifier,
    independent=True,
    multi_phase=False,
    description="{{agent_description}}",
    flow_definition=FlowDefinition(
        system_instructions=["Always respond in markdown format."],
        execution_strategy=ExecutionStrategyEnum.sequential,
        response_protocol=ResponseProtocolEnum.HTTP,
        nodes=[
            FlowNode(
                order=0,
                identifier="ai_model_call_1",
                type=FlowNodeTypeEnum.ai_model_call,
                resources=[
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "claude-3-7-sonnet"},
                        is_default=True,
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "gemini-2.0-flash"},
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "o3-mini"},
                    ),
                ],
                ai_settings=None,
                input_settings=NodeInputSettings(
                    context_sources=[],
                ),
                response_settings=NodeResponseSettings(
                    enabled=True,
                ),
            ),
            FlowNode(
                order=1,
                identifier="generate_conversation_title",
                type=FlowNodeTypeEnum.ai_model_call,
                resources=[
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={
                            ResourceQueryFieldsEnum.model_name: "gpt-4o-mini",
                            ResourceQueryFieldsEnum.api_provider: AIModelAPIProviderEnum.OPEN_AI,
                        },
                    ),
                ],
                ai_settings=AISettings(
                    system_instructions=[
                        "You are a summarizer which generate a title text under 60 characters from the prompts.",
                    ],
                    node_prompt=PromptTemplate(
                        template="Summarize in plane text under {number_of_chars} characters.",
                        default_values={
                            "number_of_chars": 60,
                        },
                    ),
                    options_overrides=None,
                ),
                input_settings=NodeInputSettings(
                    context_sources=[SpecialNodeIdEnum.PREVIOUS],
                ),
                response_settings=NodeResponseSettings(
                    enabled=True,
                ),
            ),
        ],
    ),
)
