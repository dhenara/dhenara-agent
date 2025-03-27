import asyncio

from dhenara.agent.dsl import AIModelNodeInput, FlowNodeTypeEnum, NodeInputRequiredEvent


async def async_input(prompt: str) -> str:
    """Asynchronous version of input function"""
    # Use event loop to run input in a thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))


async def ai_model_input_handler(event: NodeInputRequiredEvent):
    print(f"received event {event.as_dict()}\n\n")

    if event.node_type == FlowNodeTypeEnum.ai_model_call:
        if event.node_id == "ai_model_call_1":
            user_query = await async_input("Enter your query: ")
            event.input = AIModelNodeInput(prompt_variables={"user_query": user_query})
            event.handled = True
        elif event.node_id == "generate_code":
            language = await async_input("Enter programming language: ")
            event.input = AIModelNodeInput(prompt_variables={"language": language})
            event.handled = True
