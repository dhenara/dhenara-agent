chatbot_with_summarizer_json = {
    "name": "Simple Chatbot Flow",
    "description": "This flow will call a text-generation AI model in sync mode and return output",
    "definition": {
        "system_instructions": [
            "Always respond in markdown format.",
        ],
        "execution_strategy": "sequential",
        "response_protocol": "http",  # http_sse
        "nodes": [
            {
                "order": 0,
                "identifier": "ai_model_call_1",
                "type": "ai_model_call",
                "resources": [
                    {
                        "item_type": "ai_model_endpoint",
                        "query": {"model_name": "gpt-4o-mini"},
                        "is_default": True,
                    },
                    {
                        "item_type": "ai_model_endpoint",
                        "query": {"model_name": "gpt-4o"},
                    },
                    {
                        "item_type": "ai_model_endpoint",
                        "query": {"model_name": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"},
                    },
                    {
                        "item_type": "ai_model_endpoint",
                        "query": {"model_name": "claude-3-5-haiku-20241022"},
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
                        "context_sources": [],
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
                },
                "pre_actions": [],
                "post_actions": [],
            },
            {
                "order": 1,
                "identifier": "generate_conversation_title",
                "type": "ai_model_call",
                "resources": [
                    {
                        "item_type": "ai_model_endpoint",
                        "query": {"model_name": "gpt-4o-mini"},
                    },
                ],
                "ai_settings": {
                    "system_instructions": [
                        "You are a summarizer which generate a title text under 60 characters from the prompts.",
                    ],
                    "node_prompt": {
                        "pre_prompt": None,
                        "prompt": [
                            "Summarize in plane text under 60 characters.",
                        ],
                        "post_prompt": None,
                    },
                    "options_overrides": None,
                },
                "input_settings": {
                    "input_source": {
                        "user_input_sources": [],
                        "context_sources": ["previous"],
                    },
                },
                "storage_settings": {
                    "save": {
                        "conversation": ["title"],
                        "conversation_node": [],
                    },
                    "delete": {},
                },
                "response_settings": {
                    "enabled": True,
                },
                "pre_actions": [],  # call truncation fn
                "post_actions": [],
            },
        ],
    },
}
