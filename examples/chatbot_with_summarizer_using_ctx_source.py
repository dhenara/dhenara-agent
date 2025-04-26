from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    EventType,
    FlowDefinition,
    NodeRecordSettings,
    SpecialNodeIDEnum,
)
from dhenara.ai.types import (
    AIModelAPIProviderEnum,
    AIModelCallConfig,
    Prompt,
    PromptMessageRoleEnum,
    PromptText,
    ResourceConfigItem,
    ResourceConfigItemTypeEnum,
    ResourceQueryFieldsEnum,
    TextTemplate,
)

test_mode = False


chatbot_flow = (
    FlowDefinition()
    .node(
        "ai_model_call_1",
        AIModelNode(
            resources=[
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "gpt-4o-mini"},
                    is_default=True,
                ),
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "claude-3-7-sonnet"},
                ),
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "gemini-2.0-flash-lite"},
                ),
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "o3-mini"},
                ),
            ],
            pre_events=[EventType.node_input_required],
            settings=AIModelNodeSettings(
                system_instructions=[
                    "You are an AI assistant in a general purpose chatbot",
                    "Always respond in markdown format.",
                ],
                prompt=Prompt(
                    role=PromptMessageRoleEnum.USER,
                    text=PromptText(
                        content=None,
                        template=TextTemplate(
                            text="$var{user_query}",
                            variables={"user_query": {}},
                        ),
                    ),
                ),
                model_call_config=AIModelCallConfig(
                    # structured_output=CodePlan,
                    test_mode=test_mode,
                ),
            ),
            record_settings=NodeRecordSettings.with_outcome_format("text"),  # Enforce test as default is json
        ),
    )
    .node(
        "title_generator",
        AIModelNode(
            resources=[
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={
                        ResourceQueryFieldsEnum.model_name: "gpt-4o-mini",
                        ResourceQueryFieldsEnum.api_provider: AIModelAPIProviderEnum.OPEN_AI,
                    },
                ),
            ],
            settings=AIModelNodeSettings(
                system_instructions=[
                    "You are a summarizer which generate a title text under 60 characters from the prompts.",
                ],
                prompt=Prompt.with_dad_text(
                    text="Summarize in plane text under $var{number_of_chars} characters.",
                    variables={
                        "number_of_chars": {
                            "default": 60,
                            "allowed": range(50, 100),
                        },
                    },
                ),
                context_sources=[SpecialNodeIDEnum.PREVIOUS],
                model_call_config=AIModelCallConfig(
                    test_mode=test_mode,
                ),
            ),
            record_settings=NodeRecordSettings.with_outcome_format("text"),  # Enforce test as default is json
        ),
    )
)
