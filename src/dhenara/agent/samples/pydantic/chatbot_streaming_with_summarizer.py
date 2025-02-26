from dhenara.agent.types import (
    AISettings,
    ConversationFieldEnum,
    ConversationNodeFieldEnum,
    ExecutionStrategyEnum,
    Flow,
    FlowDefinition,
    FlowNode,
    FlowNodeTypeEnum,
    NodeInputSettings,
    NodeInputSource,
    NodePrompt,
    NodeResponseSettings,
    Resource,
    ResourceObjectTypeEnum,
    ResourceQueryFieldsEnum,
    ResponseProtocolEnum,
    SpecialNodeIdEnum,
    StorageEntityTypeEnum,
    StorageSettings,
)

chatbot_streaming_with_summarizer = Flow(
    name="Simple Chatbot Flow",
    description="This flow will call a text-generation AI model in sync mode and return output",
    definition=FlowDefinition(
        system_instructions=["Always respond in markdown format."],
        execution_strategy=ExecutionStrategyEnum.sequential,
        response_protocol=ResponseProtocolEnum.HTTP_SSE,
        nodes=[
            FlowNode(
                order=0,
                identifier="ai_model_call_1",
                type=FlowNodeTypeEnum.ai_model_call_stream,
                resources=[
                    Resource(
                        object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                        object_id=None,
                        query={ResourceQueryFieldsEnum.model_name: "gpt-4o-mini"},
                        is_default=True,
                    ),
                    Resource(
                        object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                        object_id=None,
                        query={ResourceQueryFieldsEnum.model_name: "gpt-4o"},
                    ),
                    Resource(
                        object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                        object_id=None,
                        query={ResourceQueryFieldsEnum.model_name: "o3-mini"},
                    ),
                    Resource(
                        object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                        object_id=None,
                        query={ResourceQueryFieldsEnum.model_name: "DeepSeek-R1"},
                    ),
                    Resource(
                        object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                        object_id=None,
                        query={ResourceQueryFieldsEnum.model_name: "claude-3-7-sonnet"},
                    ),
                    Resource(
                        object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                        object_id=None,
                        query={ResourceQueryFieldsEnum.model_name: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"},
                    ),
                    Resource(
                        object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                        object_id=None,
                        query={ResourceQueryFieldsEnum.model_name: "claude-3-5-haiku"},
                    ),
                    Resource(
                        object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                        object_id=None,
                        query={ResourceQueryFieldsEnum.model_name: "gemini-1.5-pro"},
                    ),
                    Resource(
                        object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                        object_id=None,
                        query={ResourceQueryFieldsEnum.model_name: "gemini-1.5-flash"},
                    ),
                ],
                ai_settings=AISettings(
                    system_instructions=[],
                    node_prompt=None,
                    options_overrides=None,
                ),
                input_settings=NodeInputSettings(
                    input_source=NodeInputSource(
                        user_input_sources=[SpecialNodeIdEnum.FULL],
                        node_output_sources=[],
                    ),
                ),
                storage_settings=StorageSettings(
                    save={
                        StorageEntityTypeEnum.conversation_node: [
                            ConversationNodeFieldEnum.inputs,
                            ConversationNodeFieldEnum.outputs,
                        ],
                    },
                    delete={},
                ),
                response_settings=NodeResponseSettings(
                    enabled=True,
                ),
                pre_actions=[],
                post_actions=[],
            ),
            FlowNode(
                order=1,
                identifier="generate_conversation_title",
                type=FlowNodeTypeEnum.ai_model_call,
                resources=[
                    Resource(
                        object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                        object_id=None,
                        query={
                            ResourceQueryFieldsEnum.model_name: "gpt-4o-mini",
                        },
                    ),
                ],
                ai_settings=AISettings(
                    system_instructions=[
                        "You are a summarizer which generate a title text under 60 characters from the prompts.",
                    ],
                    node_prompt=NodePrompt(
                        pre_prompt=None,
                        prompt=["Summarize in plane text under 60 characters."],
                        post_prompt=None,
                    ),
                    options_overrides=None,
                ),
                input_settings=NodeInputSettings(
                    input_source=NodeInputSource(
                        user_input_sources=[],
                        node_output_sources=[SpecialNodeIdEnum.PREVIOUS],
                    ),
                ),
                storage_settings=StorageSettings(
                    save={
                        StorageEntityTypeEnum.conversation: [ConversationFieldEnum.title],
                        StorageEntityTypeEnum.conversation_node: [],
                    },
                    delete={},
                ),
                response_settings=NodeResponseSettings(
                    enabled=True,
                ),
                pre_actions=[],
                post_actions=[],
            ),
        ],
    ),
)
