call_ai_model_with_user_input = {
    "name": "Generic Text Generateion Flow",
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
            "config": {},
            "save_output": True,
            "output_actions": ["update_internal_data", "send_response"],
        },
        {
            "identifier": "generate_summary_1",
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
            "config": {},
            "output_action": "send_response",
        },
    ],
    "execution_strategy": "sequential",
}

call_ai_model_with_user_input_2 = {
    "name": "Generic Text Generateion Flow 2",
    "description": "This flow will call a text-generation AI model in sync mode and return output",
    "nodes": [
        {
            "identifier": "",
            "type": "retrieve_inhouse_data",
            "optional": True,
            "order": 0,
            "config": {
                "model_id": str,
                "model_type": "",
                "resource_ep_id": None,
                "resource_name": "gpt_4o",
                "options": None,
            },
        },
        {
            "identifier": "texgen_ai_model_call",
            "type": "ai_model_sync",
            "order": 0,
            "config": {
                "resource_ep_id": None,
                "resource_name": "gpt_4o",
                "options": None,
            },
        },
        {
            "identifier": "generate_summary",
            "type": "ai_model_sync",
            "order": 1,
            "config": {"model_name": "gpt-4"},
        },
    ],
    "execution_strategy": "sequential",
}
