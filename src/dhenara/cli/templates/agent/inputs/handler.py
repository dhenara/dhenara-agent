import asyncio

from dhenara.agent.dsl import AIModelNodeInput, FlowNodeTypeEnum, NodeInputRequiredEvent


async def _async_input_helper(prompt: str) -> str:
    """Asynchronous version of input function"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))


async def event_handler(event: NodeInputRequiredEvent):
    if event.node_type == FlowNodeTypeEnum.ai_model_call:
        if event.node_id == "ai_model_call_1":
            user_query = await _async_input_helper("Enter your query: ")
            event.input = AIModelNodeInput(prompt_variables={"user_query": user_query})
            event.handled = True
