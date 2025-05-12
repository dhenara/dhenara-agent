from dhenara.agent.dsl import (
    FlowNodeTypeEnum,
    NodeInputRequiredEvent,
)
from dhenara.agent.utils.helpers.terminal import async_input, get_ai_model_node_input


async def node_input_event_handler(event: NodeInputRequiredEvent):
    node_input = None
    if event.node_type == FlowNodeTypeEnum.ai_model_call:
        if event.node_id == "user_query_processor":
            node_input = await get_ai_model_node_input(
                node_def_settings=event.node_def_settings,
            )
            user_query = await async_input("Enter your query: ")
            node_input.prompt_variables = {"user_query": user_query}

        event.input = node_input
        event.handled = True
