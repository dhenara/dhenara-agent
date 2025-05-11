from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    EventType,
    FlowDefinition,
    NodeRecordSettings,
)
from dhenara.ai.types import (
    AIModelCallConfig,
    Prompt,
    ResourceConfigItem,
)

main_flow = FlowDefinition()
main_flow.node(
    "ai_model_call_1",
    AIModelNode(
        resources=ResourceConfigItem.with_models(
            [
                "claude-3-5-haiku",
                "gpt-4.1-nano",
                "gemini-2.0-flash-lite",
            ]
        ),
        pre_events=[EventType.node_input_required],
        settings=AIModelNodeSettings(
            system_instructions=[
                "You are an AI assistant in a general purpose chatbot",
                "Always respond in markdown format.",
            ],
            prompt=Prompt.with_dad_text("$var{user_query}"),
            model_call_config=AIModelCallConfig(
                test_mode=False,
            ),
        ),
        record_settings=NodeRecordSettings.with_outcome_format("text"),
    ),
)
main_flow.node(
    "title_generator",
    AIModelNode(
        resources=ResourceConfigItem.with_model("gpt-4o-mini"),
        settings=AIModelNodeSettings(
            system_instructions=[
                "You are a summarizer which generate a title.",
            ],
            prompt=Prompt.with_dad_text(
                "Summarize in plane text under 60 characters. $expr{ $hier{ai_model_call_1}.outcome.text }",
            ),
        ),
        record_settings=NodeRecordSettings.with_outcome_format("text"),
    ),
)
