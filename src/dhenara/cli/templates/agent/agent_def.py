from dhenara.agent.types import (
    Agent,
    AISettings,
    ExecutionStrategyEnum,
    FlowDefinition,
    FlowNode,
    FlowNodeTypeEnum,
    NodeInputSettings,
    NodeInputSource,
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

agent_def = Agent(
    identifier="chatbot",
    independent=True,
    multi_phase=False,
    description="Simple Chatbot Agen. This flow will call a text-generation AI model in sync mode and return output",
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
                    input_source=NodeInputSource(
                        user_input_sources=[SpecialNodeIdEnum.FULL],
                        context_sources=[],
                    ),
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
                    input_source=NodeInputSource(
                        user_input_sources=[],
                        context_sources=[SpecialNodeIdEnum.PREVIOUS],
                    ),
                ),
            ),
        ],
    ),
)
