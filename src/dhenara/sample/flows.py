call_ai_model_with_user_input = {
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
                    "query": {"api_model_name": "gpt-4o-mini"},
                },
                {
                    "model_type": "ai_model_endpoint",
                    "object_id": None,
                    "query": {"api_model_name": "gpt-4o"},
                },
                {
                    "model_type": "ai_model_endpoint",
                    "object_id": None,
                    "query": {"api_model_name": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"},
                },
                {
                    "model_type": "ai_model_endpoint",
                    "object_id": None,
                    "query": {"api_model_name": "claude-3-5-haiku-20241022"},
                },
            ],
            "resource_config": {
                "system_instructions": None,
                "pre_prompt": None,
                "prompt": None,
                "post_prompt": None,
                "options_overrides": {},
            },
            "config": {},
            "output_actions": ["save_to_conversation_node", "send_result_and_status"],
        },
        {
            "identifier": "generate_conversation_title",
            "type": "ai_model_sync",
            "bypass_mode": True,
            "order": 1,
            "resources": [
                {
                    "model_type": "ai_model_endpoint",
                    "object_id": None,
                    "query": {"api_model_name": "gpt-4o-mini"},
                },
            ],
            "resource_config": {
                "system_instructions": [
                    "You are a summarizer which generate a title text under 60 characters from the promts",
                ],
                "pre_prompt": None,
                "prompt": [
                    "Summarize in plane text under 60 characters.",
                ],
                "post_prompt": None,
                "options_overrides": {},
            },
            "config": {},
            "output_actions": ["update_conversation_node_title", "send_push_notification"],
        },
    ],
    "execution_strategy": "sequential",
    "resource_config": {
        "system_instructions": "Always respond in markdown format.",
    },
}
