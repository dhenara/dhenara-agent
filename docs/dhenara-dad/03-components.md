# Dhenara Agent DSL (DAD) - Components

## Component Overview

Components are the building blocks of the Dhenara Agent DSL. They provide structured ways to define AI agent behaviors and workflows. The component system in DAD is hierarchical, with high-level components (like agents) containing and coordinating lower-level components (like flows).

## Core Component Types

### FlowDefinition

A Flow is a directed sequence of connected nodes that process data. Think of it as a pipeline where data flows through a series of processing steps.

```python
from dhenara.agent.dsl import FlowDefinition, AIModelNode

# Create a flow definition
my_flow = FlowDefinition()

# Add nodes to the flow
my_flow.node("first_node", AIModelNode(...))
my_flow.node("second_node", SomeOtherNode(...))

# Connect nodes (if needed beyond default sequential flow)
my_flow.connect("first_node", "second_node")
```

### AgentDefinition

An Agent is a higher-level component that can coordinate multiple flows and implement more complex behaviors.

```python
from dhenara.agent.dsl import AgentDefinition, FlowDefinition

# Create an agent definition
my_agent = AgentDefinition()

# Define flows within the agent
planning_flow = FlowDefinition()
# ... define planning flow nodes

execution_flow = FlowDefinition()
# ... define execution flow nodes

# Add flows to the agent
my_agent.flow("planning", planning_flow)
my_agent.flow("execution", execution_flow)
```

### ComponentDefinition

This is the base class for all components in DAD. Both FlowDefinition and AgentDefinition inherit from it. It provides the common functionality for component definition and management.

## Node System

Nodes are the individual processing units within flows. DAD comes with several built-in node types:

### AIModelNode

Interacts with AI models (like GPT-4, Claude) to process text and generate responses.

```python
from dhenara.agent.dsl import AIModelNode, AIModelNodeSettings
from dhenara.ai.types import Prompt, ResourceConfigItem

ai_node = AIModelNode(
    resources=ResourceConfigItem.with_model("claude-3-5-sonnet"),
    settings=AIModelNodeSettings(
        system_instructions=["You are a helpful assistant."],
        prompt=Prompt.with_dad_text("Generate ideas for: $var{topic}"),
    ),
)
```

### FileOperationNode

Performs file system operations like reading, writing, and manipulating files.

```python
from dhenara.agent.dsl import FileOperationNode, FileOperationNodeSettings

file_node = FileOperationNode(
    settings=FileOperationNodeSettings(
        base_directory="/path/to/workspace",
        stage=True,
        commit=True,
        commit_message="Update files based on analysis",
    ),
)
```

### FolderAnalyzerNode

Analyzes directory structures and file contents to provide context to other nodes.

```python
from dhenara.agent.dsl import FolderAnalyzerNode, FolderAnalyzerSettings
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import FolderAnalysisOperation

analyzer_node = FolderAnalyzerNode(
    settings=FolderAnalyzerSettings(
        base_directory="/path/to/repo",
        operations=[
            FolderAnalysisOperation(
                operation_type="analyze_folder",
                path="src",
                recursive=True,
            )
        ],
    ),
)
```

### Custom Nodes

DAD is extensible, allowing you to create custom node types for specific use cases:

```python
from dhenara.agent.dsl.base import Node, NodeDefinition, NodeSettings

class MyCustomNodeSettings(NodeSettings):
    custom_param: str
    other_param: int = 10

class MyCustomNode(NodeDefinition):
    node_type = "custom"
    settings_class = MyCustomNodeSettings
    
    # Implementation details...
```

## Node Input and Output

Nodes communicate through typed inputs and outputs:

```python
from dhenara.agent.dsl.base import NodeInput, NodeOutput
from pydantic import BaseModel

class CustomInput(NodeInput):
    query: str
    max_results: int = 10

class CustomOutput(NodeOutput):
    results: list[str]
    processing_time: float
```

## Events and Communication

Nodes can communicate through events, allowing for dynamic, event-driven flows:

```python
from dhenara.agent.dsl.events import EventType

# Node that responds to input required events
my_node = AIModelNode(
    pre_events=[EventType.node_input_required],
    # Other settings...
)

# Register an event handler in the run context
run_context.register_node_input_handler(my_input_handler_function)
```

## Component Execution

Components are executed using runners:

```python
from dhenara.agent.runner import FlowRunner
from dhenara.agent.run import RunContext
from pathlib import Path

# Create a run context
run_context = RunContext(
    root_component_id="my_flow",
    project_root=Path("."),
)

# Create a runner for the flow
runner = FlowRunner(my_flow, run_context)

# Setup and run the flow
runner.setup_run()
await runner.run()
```

## Component Hierarchies

Components can be organized in hierarchies, with parent components managing child components:

```python
# Parent agent with multiple flows
agent = AgentDefinition()

# Child flows
data_collection = FlowDefinition()
# Add nodes to data_collection...

analysis = FlowDefinition()
# Add nodes to analysis...

# Add flows to agent
agent.flow("collect", data_collection)
agent.flow("analyze", analysis)

# Sequence the flows
agent.sequence(["collect", "analyze"])
```

This hierarchical structure allows for complex agent behaviors to be broken down into manageable, reusable components.
