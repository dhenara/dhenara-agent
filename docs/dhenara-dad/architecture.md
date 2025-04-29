# Dhenara Agent DSL (DAD): Architecture Deep Dive

## Architecture Overview

Dhenara Agent DSL (DAD) implements a component-based architecture designed around clear separation of concerns and hierarchical composition. This document provides a detailed explanation of the architecture, its core components, and how they interact.

## Core Architectural Components

### 1. Base Abstractions

At the foundation of Dhenara Agent DSL are several key abstractions that define the behavior of executable elements:

- **Executable**: The core interface for anything that can be executed within the system
- **ExecutableNode**: A specific type of executable that represents an atomic unit of work
- **ExecutableComponent**: A composite executable that contains other executables
- **ExecutionContext**: Manages state during execution and provides access to resources

### 2. Component Hierarchy

The system uses a three-level hierarchy of components:

```
Agent
 ├── Flow 1
 │    ├── Node A
 │    ├── Node B
 │    └── Subflow
 │         ├── Node C
 │         └── Node D
 ├── Flow 2
 │    ├── Node E
 │    └── Node F
 └── Subagent
      └── Flow 3
           ├── Node G
           └── Node H
```

- **Nodes** (Leaf components): Atomic units of execution that perform specific tasks such as making LLM API calls, analyzing files, or performing file operations
- **Flows** (Intermediate components): Collections of nodes and subflows that define execution logic, including support for sequential execution, conditionals, and loops
- **Agents** (Root components): Top-level components that can contain flows and other agents, representing complete functional units

### 3. Definition and Execution Pattern

Each component follows a clear separation between its definition (what it does) and execution (how it runs):

- **Definition Classes**: `NodeDefinition`, `FlowDefinition`, `AgentDefinition`
- **Executable Classes**: `ExecutableNode`, `Flow`, `Agent`
- **Executor Classes**: `NodeExecutor`, `FlowExecutor`, `AgentExecutor`

This separation enables flexible composition and customization while maintaining consistent execution behaviors.

### 4. Execution Context and State Management

The `ExecutionContext` is a crucial component that:

- Tracks the execution state (pending, running, completed, failed)
- Stores results from previously executed nodes
- Manages hierarchical variable scoping
- Provides access to resources (e.g., LLM models) and artifact storage
- Enables components to communicate with each other

```
ExecutionContext
 ├── Executable Type
 ├── Component Definition
 ├── Parent Context (optional)
 ├── Execution Results
 ├── Artifact Manager
 ├── Resource Configuration
 └── Event Bus
```

The execution context creates a hierarchical structure that mirrors the component hierarchy, allowing child components to access resources and results from their parent contexts.

### 5. Event System

The event system provides a publish-subscribe mechanism for communication between components:

- Events have a type (e.g., `node_input_required`) and nature (notify, with_wait, with_future)
- Components can register handlers for specific event types
- Events can be used to request inputs, notify of execution status changes, or signal completion

This enables loose coupling between components and supports extensibility through custom event handlers.

### 6. Template Engine

The template engine is a powerful feature that enables dynamic text generation and processing:

- **Variable Substitution**: Replace `$var{name}` with the value of a variable
- **Expression Evaluation**: Evaluate expressions like `$expr{1 + 2}` or `$expr{user.name}`
- **Hierarchical References**: Access results from other nodes using `$hier{node_id.property}`
- **Python Expressions**: Evaluate Python code with `$expr{py: len(items)}`

The template engine makes it easy to build dynamic prompts, process responses, and coordinate between components.

### 7. Registry and Resource Management

The system includes registries for managing:

- Execution contexts: Track and access execution contexts by path
- Node executors: Map node types to their executor implementations
- Resources: Manage access to external resources like LLM models

These registries ensure proper resource management and enable components to find and use the resources they need.

## Execution Flow

The execution flow in Dhenara Agent DSL follows these general steps:

1. An agent, flow, or node is created with a specific definition
2. When executed, the component's executor orchestrates the execution:
   - For agents and flows, this means executing their child components in the appropriate order
   - For nodes, this means performing the specific action defined by the node
3. Results are stored in the execution context
4. Events are triggered as needed for input, coordination, or notification
5. The template engine processes any templates, expressions, or references

This execution flow ensures consistent behavior while allowing for flexible composition and extension.

## Component Types

### Node Types

Nodes are the atomic units of execution, and Dhenara Agent DSL includes several built-in node types:

- **AIModelNode**: Makes calls to AI models, handling prompts, contexts, and responses
- **CommandNode**: Executes shell commands and captures outputs
- **FileOperationNode**: Performs file operations like create, edit, delete, and move
- **FolderAnalyzerNode**: Analyzes folder structures and extracts information

Custom node types can be created by extending the appropriate base classes and registering them with the system.

### Flow Types

Flows define the execution logic for collections of nodes and subflows:

- **Sequential Flows**: Execute nodes in sequence
- **Conditional Flows**: Execute different branches based on conditions
- **Loop Flows**: Execute a flow repeatedly for each item in a collection

Flows can be nested to create complex execution patterns while maintaining clear structure.

### Agent Types

Agents are the top-level components that represent complete functional units:

- **Standard Agents**: Execute flows and subagents in a defined order
- **Conditional Agents**: Execute different agents based on conditions
- **Loop Agents**: Execute an agent repeatedly for each item in a collection

Agents can be composed to create multi-agent systems that work together to solve complex problems.

## System Boundaries and Integration Points

Dhenara Agent DSL integrates with several external systems and services:

- **LLM Providers**: Connect to various LLM providers through the Dhenara core library
- **File System**: Interact with the file system for storage and manipulation
- **Shell Environment**: Execute commands in the host environment
- **Observability Systems**: Export metrics and traces for monitoring and debugging

These integration points allow Dhenara Agent DSL to leverage existing tools and services while providing a consistent, high-level API for agent development.

## Summary

The Dhenara Agent DSL (DAD) architecture provides a flexible, extensible foundation for building AI agent systems. By separating concerns, enabling hierarchical composition, and providing powerful abstractions, it makes it easier to create complex agent behaviors while maintaining clarity and reusability.
