# TODO: This doc is obsolete. Do not refer

# Dhenara Agent Framework Technical Overview

## Project Scope

The `dhenara-agent` package is an extensible framework for creating, configuring, and managing AI agents. Built on top of the base `dhenara` package (which simplifies LLM API calls across providers), this framework provides a structured approach to defining agent behaviors, execution flows, and integrating various capabilities.

## Core Architecture

### DSL (Domain Specific Language)

The framework implements a Python-based DSL for defining agents and their execution flows:

```python
# Define a flow with AI model nodes
flow = (
    Flow()
    .node(
        "ai_model_call_1",
        AIModelNode(
            resources=[
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "gpt-4o-mini"},
                    is_default=True,
                ),
            ],
            settings=AIModelNodeSettings(
                system_instructions=["You are an AI assistant"],
                prompt=Prompt(
                    role=PromptMessageRoleEnum.USER,
                    text=PromptText(
                        template=TextTemplate(
                            text="$var{user_query}",
                            variables={"user_query": {}},
                        ),
                    ),
                ),
            ),
        ),
    )
)

# Create an agent with the flow
agent = Agent()
agent.node(
    "agent_1",
    BasicAgentNode(
        flow=flow,
        settings=None,
    ),
)
```

### Component System

The framework is organized around a hierarchical component system:

1. **Components**: Base abstraction for executable elements (inherits from `BaseModelABC`)
   - `Agent`: High-level component that contains flows
   - `Flow`: A sequence of executable nodes

2. **Nodes**: Individual execution steps within components
   - `AIModelNode`: Interacts with LLMs
   - `CommandNode`: Executes shell commands
   - `FileOperationNode`: Performs file system operations
   - `FolderAnalyzerNode`: Analyzes repository structures
   - `BasicAgentNode`: Executes a flow as part of an agent

3. **Executors**: Runtime implementations that execute nodes
   - `AgentExecutor`, `FlowExecutor`: Manage component execution
   - `NodeExecutor`, `AIModelNodeExecutor`, etc.: Execute specific node types

### Execution Context

Execution state is managed through context objects:

- `RunContext`: Top-level execution environment
- `ExecutionContext`: Base context for all executions
- `FlowExecutionContext`, `AgentExecutionContext`: Component-specific contexts

## Key Features

### Template Engine

Advanced template system supporting variable substitution and expressions:

```python
# Simple variable substitution
"Hello $var{name}"

# Complex expressions
"Count: $expr{data.count}"
"Status: $expr{value > 10}"

# Template with DAD (Dhenara Agent DSL) context
Prompt.with_dad_text(
    text="Summarize under $var{chars} chars. $expr{previous_node.outcome.text}",
    variables={"chars": {"default": 60}},
)
```

### Resource Management

Flexible resource configuration for specifying AI model endpoints:

```python
resources=[
    ResourceConfigItem(
        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
        query={ResourceQueryFieldsEnum.model_name: "gpt-4o-mini"},
        is_default=True,
    ),
    ResourceConfigItem(
        item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
        query={ResourceQueryFieldsEnum.model_name: "claude-3-7-sonnet"},
    ),
]
```

### Event System

Event-based communication between nodes:

```python
AIModelNode(
    pre_events=[EventType.node_input_required],
    # ...
)

# Event handler
async def ai_model_node_input_handler(event: NodeInputRequiredEvent):
    user_query = await async_input("Enter your query: ")
    event.input = AIModelNodeInput(prompt_variables={"user_query": user_query})
    event.handled = True
```

### File Operations and Repository Analysis

Tools for working with file systems and analyzing code repositories:

```python
FolderAnalyzerNode(
    settings=FolderAnalyzerSettings(
        base_directory="$expr{run_root}/global_data/repo",
        operations=[
            FolderAnalysisOperation(
                operation_type="analyze_folder",
                path="src",
                max_depth=100,
                respect_gitignore=True,
                read_content=True,
            ),
        ],
    ),
)
```

### Observability

Comprehensive tracing, logging, and metrics collection:

```python
# Configure observability
observability_settings = ObservabilitySettings(
    service_name="my-agent",
    tracing_exporter_type="file",
    metrics_exporter_type="file",
    logging_exporter_type="file",
    root_log_level=logging.INFO,
)

# Trace decorator for execution tracking
@trace_node(FlowNodeTypeEnum.ai_model_call.value)
async def execute_node(self, node_id, node_definition, node_input, execution_context):
    # ...
```

### CLI Interface

Command-line tools for project and agent management:

```bash
# Create new project
dhenara startproject my_project

# Create new agent
dhenara create agent my_agent

# Run an agent
dhenara run agent my_agent

# Manage outputs
dhenara outputs list --run-id run_123
```

## Runner System

The framework provides a runner system for executing agents:

```python
# Create run context
run_context = RunContext(
    root_component_id=root_component_id,
    observability_settings=observability_settings,
    project_root=project_root,
)

# Register input handlers
run_context.register_node_input_handler(ai_model_node_input_handler)

# Create runner
runner = AgentRunner(agent, run_context)

# Run with isolation
async with IsolatedExecution(run_context) as executor:
    await executor.run(runner=runner)
```

## Artifact Management

The framework handles execution artifacts with Git integration:

```python
# Record settings in node definition
record_settings=NodeRecordSettings.with_outcome_format("text")

```

## Example Usage

The repository includes several examples demonstrating common use cases:

1. **Chatbot with Summarizer**: A two-node flow that takes user input, generates a response, and summarizes it
2. **Single-shot Coder**: An agent that analyzes code repositories and implements changes

These examples show how to build increasingly complex agents from simple components.