STREAMING_CHATBOT_FLOW = {
    "name": "Streaming Chatbot Flow",
    "description": "This flow will call a text-generation AI model in sync mode and return output",
    "definition": {
        "system_instructions": [
            "Always respond in markdown format.",
        ],
        "execution_strategy": "sequential",
        "nodes": [
            {
                "order": 0,
                "identifier": "ai_model_call_1",
                "type": "ai_model_call_stream",
                "resources": [
                    {
                        "object_type": "ai_model_endpoint",
                        "object_id": None,
                        "query": {"ai_model__api_model_name": "gpt-4o-mini"},
                        "is_default": True,
                    },
                    {
                        "object_type": "ai_model_endpoint",
                        "object_id": None,
                        "query": {"ai_model__api_model_name": "gpt-4o"},
                    },
                    {
                        "object_type": "ai_model_endpoint",
                        "object_id": None,
                        "query": {"ai_model__api_model_name": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"},
                    },
                    {
                        "object_type": "ai_model_endpoint",
                        "object_id": None,
                        "query": {"ai_model__api_model_name": "claude-3-5-haiku-20241022"},
                    },
                ],
                "ai_settings": {
                    "system_instructions": [],
                    "node_prompt": None,
                    "options_overrides": None,
                },
                "input_settings": {
                    "input_source": {
                        "user_input_sources": ["full"],
                        "node_output_sources": [],
                    },
                },
                "storage_settings": {
                    "save": {
                        "conversation": ["title"],
                        "conversation_node": ["inputs", "outputs"],
                    },
                    "delete": {},
                },
                "response_settings": {
                    "enabled": True,
                    "protocol": "http_stream",
                },
                "pre_actions": [],
                "post_actions": [],
            },
        ],
    },
}
