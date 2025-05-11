from dhenara.agent.dsl.events import NodeExecutionCompletedEvent


def print_node_completion(event: NodeExecutionCompletedEvent):
    print(f"\033[92m✓ Node {event.node_id} execution completed \033[0m")
