# Dhenara Agent DSL (DAD) - Input Handling Architecture

## Overview

Input handling is a critical component of the Dhenara Agent DSL (DAD) framework, enabling interactive configuration and dynamic behavior of agents. This document describes the architecture of the input handling system, its components, and patterns for effective implementation.

## Event-Driven Input Architecture

DAD uses an event-driven architecture for input handling, where nodes emit events when they require input, and registered handlers respond with appropriate configurations:

```python
# Node declares that it requires input
ai_node = AIModelNode(
    pre_events=[EventType.node_input_required],  # This event is emitted before execution
    resources=ResourceConfigItem.with_models("claude-3-7-sonnet"),
    settings=AIModelNodeSettings(...),
)

# Handler provides input when requested
async def input_handler(event: NodeInputRequiredEvent):
    if event.node_id == "my_node" and event.node_type == FlowNodeTypeEnum.ai_model_call:
        event.input = AIModelNodeInput(prompt_variables={"query": "user input"})
        event.handled = True  # Mark the event as handled

# Register the handler with the event bus
run_context.register_node_input_handler(input_handler)
```

This architecture provides several benefits:

1. **Separation of Concerns**: Node definitions remain clean and focused on behavior, while input handling is separate
2. **Dynamic Configuration**: Nodes can be dynamically configured at runtime
3. **Interactive Experience**: Enables rich interactive experiences with user input
4. **Reusable Components**: Input handlers can be reused across different agents

## Core Components

### NodeInputRequiredEvent

The `NodeInputRequiredEvent` is the central class for input requests:

```python
class NodeInputRequiredEvent(BaseEvent):
    event_type: str = EventType.node_input_required
    node_id: str  # ID of the node requesting input
    node_type: str  # Type of the node (ai_model_call, folder_analyzer, etc.)
    execution_context: ExecutionContext  # Context of the execution
    input: NodeInput | None = None  # Input to be provided by handler
    handled: bool = False  # Whether the event has been handled
```

When a node with `pre_events=[EventType.node_input_required]` is about to execute, it emits this event. Handlers then fill in the `input` field and mark it as `handled`.

### Node-Specific Input Classes

Each node type has its own input class that defines the configuration structure:

```python
class AIModelNodeInput(NodeInput):
    prompt_variables: dict[str, Any] = Field(default_factory=dict)
    instruction_variables: dict[str, Any] = Field(default_factory=dict)
    resources_override: list[ResourceConfigItem] | None = None
    settings_override: AIModelNodeSettings | None = None

class FolderAnalyzerNodeInput(NodeInput):
    operations: list[FolderAnalysisOperation] | None = None
    settings_override: FolderAnalyzerSettings | None = None
```

These classes provide type safety and clear structure for node configuration.

### Event Bus

The event bus manages the routing of events to handlers:

```python
# Register a handler for a specific event type
event_bus.register(EventType.node_input_required, my_handler)

# Publish an event to all registered handlers
await event_bus.publish(NodeInputRequiredEvent(node_id="my_node", ...))
```

The event bus is typically accessed through the `RunContext` which provides a simplified interface:

```python
# Register a handler through the run context
run_context.register_node_input_handler(my_handler)
```

## Common Input Patterns

### Interactive Console Input

One common pattern is to collect input from the console:

```python
async def async_input(prompt: str) -> str:
    # Use event loop to run input in a thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))

async def ai_model_node_input_handler(event: NodeInputRequiredEvent):
    if event.node_type == FlowNodeTypeEnum.ai_model_call:
        if event.node_id == "ai_model_call_1":
            user_query = await async_input("Enter your query: ")
            event.input = AIModelNodeInput(prompt_variables={"user_query": user_query})
            event.handled = True
```

This pattern is useful for simple interactive agents.

### Menu-Based Selection

For selecting from multiple options, a menu-based approach is effective:

```python
async def get_menu_choice(options: list[str], prompt: str = "Select an option:") -> int:
    print(f"\n{prompt}")
    for i, option in enumerate(options):
        print(f"  {i+1}. {option}")
    
    while True:
        try:
            choice = await async_input("Enter number: ")
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return idx
            print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")
```

This can be used for model selection or other multiple-choice scenarios.

### Complex Object Collection

For more complex inputs like folder analysis operations, a step-by-step collection approach works well:

```python
async def get_operation_input() -> FolderAnalysisOperation:
    path = await async_input("Enter path to analyze: ")
    include_content = await get_yes_no_input("Include file contents?", True)
    include_patterns = await async_input("Include patterns (comma-separated, e.g., '*.py,*.md'): ")
    exclude_patterns = await async_input("Exclude patterns (comma-separated, e.g., '*.pyc,__pycache__'): ")
    
    return FolderAnalysisOperation(
        operation_type="analyze_folder",
        path=path,
        include_content=include_content,
        include_patterns=include_patterns.split(",") if include_patterns else None,
        exclude_patterns=exclude_patterns.split(",") if exclude_patterns else None,
    )
```

This allows collection of complex structured data through a series of simple questions.

### Static Input Registration

For non-interactive scenarios, static inputs can be registered in advance:

```python
# Register static input for a specific node
run_context.register_node_static_input(
    "code_generator",
    AIModelNodeInput(prompt_variables={"task_description": "Implement feature X"})
)

# Or load from a JSON file
run_context.read_static_inputs()  # Reads from static_inputs.json
```

This is useful for batch processing or testing.

## Input Handling for Different Node Types

### AIModelNode Input Handling

AI model nodes typically require prompt variables and occasionally resource overrides:

```python
async def handle_ai_model_input(event: NodeInputRequiredEvent):
    if event.node_id == "query_analyzer":
        # Get the user query
        query = await async_input("Enter your query: ")
        
        # Select the model to use
        models = ["claude-3-7-sonnet", "gpt-4-turbo"]
        model_idx = await get_menu_choice(models, "Select model:")
        
        # Create the input
        event.input = AIModelNodeInput(
            prompt_variables={"query": query},
            resources_override=[ResourceConfigItem.with_model(models[model_idx])]
        )
        event.handled = True
```

### FolderAnalyzerNode Input Handling

Folder analyzer nodes require configuration for what to analyze:

```python
async def handle_folder_analyzer_input(event: NodeInputRequiredEvent):
    if event.node_id == "repo_analyzer":
        # Collect operations
        operations = []
        while True:
            operation = await get_operation_input()
            operations.append(operation)
            if not await get_yes_no_input("Add another analysis operation?", False):
                break
        
        # Create the input
        event.input = FolderAnalyzerNodeInput(
            settings_override=FolderAnalyzerSettings(
                base_directory="/path/to/repo",
                operations=operations,
            )
        )
        event.handled = True
```

### FileOperationNode Input Handling

File operation nodes may require specific file operations:

```python
async def handle_file_operation_input(event: NodeInputRequiredEvent):
    if event.node_id == "file_editor":
        # Get file path and operation type
        path = await async_input("Enter file path: ")
        op_type = await get_menu_choice(["create", "edit", "delete"], "Select operation:")
        
        # Handle different operation types
        if op_type == 0:  # create
            content = await get_multiline_input("Enter file content:")
            operations = [FileOperation(type="create_file", path=path, content=content)]
        elif op_type == 1:  # edit
            edits = await collect_edits()
            operations = [FileOperation(type="edit_file", path=path, edits=edits)]
        else:  # delete
            operations = [FileOperation(type="delete_file", path=path)]
        
        # Create the input
        event.input = FileOperationNodeInput(operations=operations)
        event.handled = True
```

## Advanced Input Handling Techniques

### Combined Handler

For agents with multiple nodes, a combined handler can manage all inputs:

```python
async def agent_input_handler(event: NodeInputRequiredEvent):
    # Handle based on node type and ID
    if event.node_type == FlowNodeTypeEnum.ai_model_call:
        await handle_ai_model_input(event)
    elif event.node_type == FlowNodeTypeEnum.folder_analyzer:
        await handle_folder_analyzer_input(event)
    elif event.node_type == FlowNodeTypeEnum.file_operation:
        await handle_file_operation_input(event)
```

### Context-Aware Input

Handlers can use the execution context to make decisions:

```python
async def context_aware_handler(event: NodeInputRequiredEvent):
    # Access results from previous nodes
    if event.node_id == "second_node":
        first_result = event.execution_context.get_result("first_node")
        if first_result and first_result.outcome:
            # Use previous results to inform this input
            event.input = AIModelNodeInput(
                prompt_variables={"previous_output": first_result.outcome.text}
            )
            event.handled = True
```

### Web-Based UI Integration

For more sophisticated applications, input handlers can integrate with web UIs:

```python
async def web_ui_handler(event: NodeInputRequiredEvent):
    if event.node_id == "interactive_node":
        # Send request to web UI and wait for response
        request_id = await send_input_request_to_ui(event.node_id, event.node_type)
        response = await wait_for_ui_response(request_id)
        
        # Convert UI response to node input
        event.input = convert_ui_response_to_input(response, event.node_type)
        event.handled = True
```

## Best Practices

1. **Type Safety**: Use appropriate input classes for each node type
2. **Clear Prompts**: Provide clear instructions for user input
3. **Validation**: Validate user input before creating node inputs
4. **Error Handling**: Handle input errors gracefully with appropriate feedback
5. **Timeout Handling**: Implement timeouts for user input to prevent indefinite waiting
6. **Modular Design**: Organize input handlers in a modular way for reusability
7. **State Management**: For complex inputs, consider maintaining state across prompts

## Conclusion

The input handling architecture in DAD provides a flexible, powerful system for configuring and interacting with agent nodes. By leveraging the event-driven architecture and implementing appropriate handlers, you can create rich interactive experiences while maintaining clean separation between node definition and input collection.