chatbot_streaming_json = {
    "name": "Streaming Chatbot Flow",
    "description": "This flow will call a text-generation AI model in sync mode and return output",
    "definition": {
        "system_instructions": ["Always respond in markdown format."],
        "execution_strategy": "sequential",
        "response_protocol": "http_sse",
        "nodes": [
            {
                "order": 0,
                "identifier": "ai_model_call_1",
                "type": "ai_model_call_stream",
                "input_settings": {
                    "input_source": {
                        "user_input_sources": ["full"],
                        "node_output_sources": [],
                    },
                },
                "response_settings": {
                    "enabled": True,
                },
            },
        ],
    },
}
