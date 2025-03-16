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

chatbot_with_summarizer = Agent(
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
                        query={ResourceQueryFieldsEnum.model_name: "gpt-4o-mini"},
                        is_default=True,
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "gpt-4o"},
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "o3-mini"},
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "DeepSeek-R1"},
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "claude-3-7-sonnet"},
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"},
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "claude-3-5-haiku"},
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "gemini-1.5-pro"},
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "gemini-1.5-flash"},
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "gemini-2.0-flash"},
                    ),
                    ResourceConfigItem(
                        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                        query={ResourceQueryFieldsEnum.model_name: "gemini-2.0-flash-lite"},
                    ),
                ],
                ai_settings=AISettings(
                    system_instructions=[],
                    node_prompt=None,
                    options_overrides=None,
                ),
                input_settings=NodeInputSettings(
                    context_sources=[],
                ),
                # storage_settings=StorageSettings(
                #    save={
                #        StorageEntityTypeEnum.conversation_node: [
                #            ConversationNodeFieldEnum.inputs,
                #            ConversationNodeFieldEnum.outputs,
                #        ],
                #    },
                #    delete={},
                # ),
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
                        template="Summarize in plane text under {number_of_chars} characters. {dh_input_content}",
                        default_values={
                            "number_of_chars": 60,
                        },
                    ),
                    options_overrides=None,
                ),
                input_settings=NodeInputSettings(
                    context_sources=[SpecialNodeIdEnum.PREVIOUS],
                ),
                # storage_settings=StorageSettings(
                #    save={
                #        StorageEntityTypeEnum.conversation: [ConversationFieldEnum.title],
                #        StorageEntityTypeEnum.conversation_node: [],
                #    },
                #    delete={},
                # ),
                response_settings=NodeResponseSettings(
                    enabled=True,
                ),
            ),
        ],
    ),
)
