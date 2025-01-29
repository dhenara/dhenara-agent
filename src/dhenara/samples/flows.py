SIMPLE_CHATBOT_FLOW = {
    "name": "Simple Chatbot Flow",
    "description": "This flow will call a text-generation AI model in sync mode and return output",
    "nodes": [
        {
            "identifier": "ai_model_call_1",
            "type": "ai_model_sync",
            "order": 0,
            "resources": [
                {
                    "model_type": "ai_model_endpoint",
                    "object_id": None,
                    "query": {"ai_model__api_model_name": "gpt-4o-mini"},
                    "is_default": True,
                },
                {
                    "model_type": "ai_model_endpoint",
                    "object_id": None,
                    "query": {"ai_model__api_model_name": "gpt-4o"},
                },
                {
                    "model_type": "ai_model_endpoint",
                    "object_id": None,
                    "query": {"ai_model__api_model_name": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"},
                },
                {
                    "model_type": "ai_model_endpoint",
                    "object_id": None,
                    "query": {"ai_model__api_model_name": "claude-3-5-haiku-20241022"},
                },
            ],
            "prompt_options_settings": None,
            "output_actions": ["save_to_conversation_node", "send_result_and_status"],
        },
        {
            "identifier": "generate_conversation_title",
            "type": "ai_model_sync",
            "order": 1,
            "resources": [
                {
                    "model_type": "ai_model_endpoint",
                    "object_id": None,
                    "query": {"ai_model__api_model_name": "gpt-4o-mini"},
                },
            ],
            "prompt_options_settings": {
                "system_instructions": [
                    "You are a summarizer which generate a title text under 60 characters from the promts",
                ],
                "pre_prompt": None,
                "prompt": [
                    "Summarize in plane text under 60 characters.",
                ],
                "options_overrides": {},
            },
            "output_actions": ["update_conversation_node_title", "send_push_notification"],
        },
    ],
    "execution_strategy": "sequential",
    "prompt_options_settings": {
        "system_instructions": [
            "Always respond in markdown format.",
        ],
    },
}
