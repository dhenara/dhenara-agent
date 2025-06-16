from dhenara.agent.dsl.events import ComponentExecutionCompletedEvent, NodeExecutionCompletedEvent


async def print_node_completion(event: NodeExecutionCompletedEvent):
    print(f"\033[92m✓ Node {event.node_id} execution completed \033[0m")


async def print_component_completion(event: ComponentExecutionCompletedEvent):
    print(f"\033[94m✓ {event.component_id} execution completed \033[0m")
