from dhenara.agent.dsl import AIModelNodeInput, FlowNodeTypeEnum, NodeInputRequiredEvent


# Define an input handler
async def ai_model_input_handler(event: NodeInputRequiredEvent):
    print(f"AJ: ai_model_input_handler: received event {event.as_dict()} ")

    if event.node_type == FlowNodeTypeEnum.ai_model_call:
        if event.node_id == "ai_model_call_1":
            event.input = AIModelNodeInput(
                prompt_variables={"user_query": "What is dhenara?"}
            )
            event.handled = True
        elif event.node_id == "generate_code":
            # Could collect input from user or another source
            event.input = AIModelNodeInput(prompt_variables={"language": "TypeScript"})
            event.handled = True
