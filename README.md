# Dhenara Agent DSL (DAD)

## Overview

Dhenara Agent DSL (DAD) is an open-source framework built on top of the `dhenara-ai` Python package. It provides a
powerful, expressive, and type-safe domain-specific language (DSL) for defining and executing AI agent workflows. DAD
makes it easier to create, compose, and orchestrate AI agents with sophisticated behaviors, while maintaining robust
observability and reproducibility.

For full documentation, visit [docs.dhenara.com](https://docs.dhenara.com/).


## What is Dhenara Agent DSL?

Dhenara Agent DSL or DAD (available as a Python package named `dhenara-agent`) is an AI agent framework with a strong
focus on:

1. **Expressive Agent Definition**: Create complex agent workflows using a straightforward, programming language-like
   approach
2. **Component-Based Architecture**: Compose reusable components to build sophisticated agent systems
3. **Out-of-the-box Support for Multiple LLMs**: Switch between different LLM models on the fly
4. **Comprehensive Observability**: Built-in logging, tracing, and metrics collection for all agent activities using
   OpenTelemetry and open-source exporters like Zipkin and Jaeger
5. **Reproducible Execution**: Track and replay agent execution through a run context system, reducing costs by
   rerunning failed flows without additional AI Model API calls
6. **Extensible Node System**: Easily create custom node types to extend functionality
7. **Resource Management**: Flexible management of AI model resources and credentials

## Installation

You can install the Dhenara Agent DSL framework using pip:

```bash
pip install dhenara-agent
```

## Core Concepts

### Basic Elements

DAD uses a hierarchical component model that allows for composition and reuse. It is built around three primary types of
components:

- **Execution Nodes**: Atomic execution units that perform specific functions (e.g., making an LLM API call, analyzing a
  folder, performing file operations like creating/updating files)
- **Execution Flows**: Collections of nodes or sub-flows with execution logic, supporting sequential execution,
  conditionals, and loops
- **Agents**: Higher-level abstractions that can contain flows and other agents, representing complete functional units

### Event-Driven Architecture

An event system enables loose coupling between components, allowing agents to react to events, request inputs, and
communicate with each other without tight coupling.

### Powerful Template Engine

A powerful template engine supports variable substitution, expressions, and hierarchical references, making it easy to
build dynamic prompts and process responses.

### Execution Model

The execution follows a hierarchical structure:

1. Components (Agents or Flows) define the overall structure
2. Nodes within components perform specific tasks
3. A RunContext manages the execution environment
4. Tracing, logging, and metrics provide visibility into execution

### Resource Management

DAD provides a flexible system for managing AI model resources and API credentials, making it easier to work with
different LLM providers and models.

## Usage Examples

### Basic Example

Here's a simple example of defining a flow using DAD:

```python
from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    FlowDefinition,
    ResourceConfigItem,
)
from dhenara.ai.types import Prompt

# Define a flow
my_flow = FlowDefinition()

# Add an AI model node to the flow
my_flow.node(
    "question_answerer",
    AIModelNode(
        resources=ResourceConfigItem.with_model("claude-3-5-haiku"),
        settings=AIModelNodeSettings(
            system_instructions=["You are a helpful assistant."],
            prompt=Prompt.with_dad_text("Answer the following question: $var{question}"),
        ),
    ),
)
```



## Documentation

For comprehensive documentation including tutorials, API reference, and advanced usage examples, visit [docs.dhenara.com](https://docs.dhenara.com/).