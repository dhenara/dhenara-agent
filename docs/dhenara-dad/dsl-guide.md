# Dhenara Agent DSL (DAD) Guide

## Introduction to DAD

Dhenara Agent DSL (DAD) is a domain-specific language built on top of Python that allows you to define agent behaviors in a declarative, programming language-like syntax. This guide explains the core concepts of DAD and demonstrates how to use it to create agents, flows, and nodes.

## DSL Core Concepts

DAD is built around three main types of components:

1. **Nodes**: Atomic units of execution that perform specific tasks
2. **Flows**: Collections of nodes with execution logic
3. **Agents**: Higher-level components that can contain flows and other agents

Each component is defined using a declarative syntax that describes what it does rather than how it works. The DSL then takes care of executing these components according to the defined rules.

## Defining Components

### Nodes

Nodes are the basic building blocks of DAD. Each node type serves a specific purpose:

```python
# Create an AI model node that calls an LLM
ai_node = AIModelNode(
    resources=ResourceConfigItem.with_models("claude-3-opus"),
    pre_events=[EventType.node_input_required],
    settings=AIModelNodeSettings(
        system_instructions=["You are a helpful assistant."],
        prompt=Prompt.with_text("Tell me about $var{topic}"),
        model_call_config=AIModelCallConfig(
            max_output_tokens=1000,
            options={"temperature": 0.7}
        )
    )
)

# Create a file operation node that creates a file
file_node = FileOperationNode(
    settings=FileOperationNodeSettings(
        base_directory="/path/to/directory",
        operations_template=ObjectTemplate(
            expression="$hier{ai_node}.outcome.structured.operations"
        ),
        commit=True
    )
)

# Create a folder analyzer node that analyzes a directory
analyzer_node = FolderAnalyzerNode(
    settings=FolderAnalyzerSettings(
        base_directory="/path/to/directory",
        operations=[
            FolderAnalysisOperation(
                operation_type="analyze_folder",
                path="src",
                include_patterns=["*.py"],
                exclude_patterns=["__pycache__"],
                include_content=True
            )
        ]
    )
)
```

### Flows

Flows combine nodes into sequences, conditionals, and loops:

```python
# Create a flow definition
my_flow = FlowDefinition()

# Add nodes to the flow
my_flow.node("analyzer", analyzer_node)
my_flow.node("ai_processor", ai_node)
my_flow.node("file_writer", file_node)

# Create a conditional branch within a flow
condition_flow = FlowDefinition()

# Define true and false branches
true_branch = FlowDefinition().node("success_action", success_node)
false_branch = FlowDefinition().node("fallback_action", fallback_node)

# Add conditional to the flow
condition_flow.conditional(
    "condition_check",
    statement=ObjectTemplate(expression="$hier{ai_processor}.outcome.structured.success == True"),
    true_branch=true_branch,
    false_branch=false_branch
)

# Create a loop flow
loop_flow = FlowDefinition()

# Define loop body
loop_body = FlowDefinition().node("process_item", process_node)

# Add loop to the flow
loop_flow.for_each(
    "process_items",
    statement=ObjectTemplate(expression="$hier{analyzer}.outcome.structured.files"),
    body=loop_body,
    max_iterations=10,
    item_var="current_item",
    index_var="item_index"
)
```

### Agents

Agents are top-level components that can contain flows and other agents:

```python
# Create an agent definition
my_agent = AgentDefinition()

# Add a flow to the agent
my_agent.flow("main_flow", my_flow)

# Add a subagent to the agent
my_agent.subagent("helper_agent", helper_agent)

# Create a conditional agent
conditional_agent = AgentDefinition()

# Define true and false branches
true_branch_agent = AgentDefinition().flow("true_flow", true_flow)
false_branch_agent = AgentDefinition().flow("false_flow", false_flow)

# Add conditional to the agent
conditional_agent.conditional(
    "condition_check",
    statement=ObjectTemplate(expression="$hier{main_flow.analyzer}.outcome.structured.file_count > 10"),
    true_branch=true_branch_agent,
    false_branch=false_branch_agent
)
```

## Template System

DAD includes a powerful template system that lets you work with dynamic values:

### Variable Substitution

Use `$var{name}` to substitute variables:

```python
prompt=Prompt.with_text("Generate code for a $var{language} function that $var{task}")
```

### Expressions

Use `$expr{...}` to evaluate expressions:

```python
prompt=Prompt.with_text("Your task has $expr{item_count} items, taking $expr{item_count * 5} minutes")
```

### Hierarchical References

Use `$hier{...}` to access results from other nodes:

```python
prompt=Prompt.with_text("Analyze this code: $hier{analyzer}.outcome.text")
```

### Python Expressions

Use `$expr{py: ...}` to evaluate Python code:

```python
condition=ObjectTemplate(expression="$expr{py: len($hier{analyzer}.outcome.structured.files) > 5}")
```

## Event System

The event system enables components to communicate and request information:

### Pre-Events

Events that occur before a node executes:

```python
ai_node = AIModelNode(
    pre_events=[EventType.node_input_required],
    # ...
)
```

### Event Handlers

Functions that handle specific events:

```python
async def handle_input_required(event: NodeInputRequiredEvent):
    if event.node_id == "ai_processor":
        event.input = AIModelNodeInput(
            prompt_variables={"topic": "artificial intelligence"}
        )
        event.handled = True

# Register the handler
event_bus.register(EventType.node_input_required, handle_input_required)
```

## Execution Context

The execution context manages state during execution:

```python
# Execute an agent with a specific context
result = await my_agent.execute(
    execution_context=AgentExecutionContext(
        component_id="my_agent",
        component_definition=my_agent,
        run_context=run_context
    )
)
```

## Common Patterns

### Single-Shot Agent

A simple agent that performs a single sequence of operations:

```python
# Single-shot agent for code generation
code_generator = AgentDefinition()

# Define the flow
gen_flow = FlowDefinition()
gen_flow.node("analyzer", FolderAnalyzerNode(...))
gen_flow.node("generator", AIModelNode(...))
gen_flow.node("file_writer", FileOperationNode(...))

# Add the flow to the agent
code_generator.flow("main_flow", gen_flow)
```

### Multi-Step Agent

An agent that performs multiple steps with dependencies:

```python
# Multi-step agent for analyzing and transforming data
data_agent = AgentDefinition()

# Define the flows
analysis_flow = FlowDefinition()
analysis_flow.node("data_loader", DataLoaderNode(...))
analysis_flow.node("analyzer", AIModelNode(...))

transform_flow = FlowDefinition()
transform_flow.node("transformer", AIModelNode(
    settings=AIModelNodeSettings(
        context_sources=["analysis_flow.analyzer"]
    )
))
transform_flow.node("output_writer", FileOperationNode(...))

# Add the flows to the agent
data_agent.flow("analysis", analysis_flow)
data_agent.flow("transform", transform_flow)
```

### Recursive Agent

An agent that can call itself recursively for complex tasks:

```python
# Recursive agent for solving complex problems
solver = AgentDefinition()

# Define the main flow
main_flow = FlowDefinition()
main_flow.node("problem_analyzer", AIModelNode(...))

# Define the recursive logic
recursion_check = FlowDefinition()

# Branches for recursion
recursive_branch = FlowDefinition()
recursive_branch.node("decompose", AIModelNode(...))
recursive_branch.node("recursive_call", RecursiveFlowNode(...))

direct_branch = FlowDefinition()
direct_branch.node("direct_solver", AIModelNode(...))

# Add conditional to the flow
recursion_check.conditional(
    "check_complexity",
    statement=ObjectTemplate(expression="$hier{problem_analyzer}.outcome.structured.complexity > 7"),
    true_branch=recursive_branch,
    false_branch=direct_branch
)

# Add flows to the agent
solver.flow("analyze", main_flow)
solver.flow("solve", recursion_check)
```

## Best Practices

### Component Organization

- Keep nodes focused on a single responsibility
- Organize flows to represent logical steps in a process
- Use agents to encapsulate complex behaviors

### Variable Naming

- Use descriptive names for nodes and components
- Follow a consistent naming convention
- Document the purpose of each component

### Error Handling

- Use conditional flows to handle errors
- Provide fallback behaviors for critical operations
- Log errors and outcomes for debugging

### Performance

- Minimize dependencies between components
- Use caching where appropriate
- Batch operations when possible

## Conclusion

Dhenara Agent DSL (DAD) provides a powerful, flexible way to define agent behaviors. By combining nodes, flows, and agents with the template and event systems, you can create sophisticated AI agents that perform complex tasks while maintaining clear, maintainable code.
