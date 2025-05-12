from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    EventType,
    FlowDefinition,
)
from dhenara.ai.types import AIModelCallConfig, Prompt

main_flow = FlowDefinition()
main_flow.node(
    "user_query_processor",
    AIModelNode(
        pre_events=[EventType.node_input_required],
        settings=AIModelNodeSettings(
            models=[
                "claude-3-5-haiku",
                "gpt-4.1-nano",
                "gemini-2.0-flash-lite",
            ],
            system_instructions=[
                "You are an AI assistant in a general purpose chatbot",
                "Always respond in markdown format.",
            ],
            prompt=Prompt.with_dad_text("$var{user_query}"),
            model_call_config=AIModelCallConfig(
                test_mode=False,
            ),
        ),
    ),
)
main_flow.node(
    "title_generator",
    AIModelNode(
        settings=AIModelNodeSettings(
            models=["gpt-4o-mini"],
            system_instructions=[
                "You are a summarizer which generate a title.",
            ],
            prompt=Prompt.with_dad_text(
                "Summarize in plain text under 60 characters. $expr{ $hier{user_query_processor}.outcome.text }",
            ),
        ),
    ),
)
