# Dhenara Agent DSL (DAD) - Introduction

## Overview

Dhenara Agent DSL (DAD) is an open-source framework built on top of the `dhenara` Python package. It provides a powerful, expressive, and type-safe domain-specific language (DSL) for defining and executing AI agent workflows. DAD makes it easier to create, compose, and orchestrate AI agents with sophisticated behaviors, while maintaining robust observability and reproducibility.

## Key Features

- **Expressive Agent Definition**: Create complex agent workflows using a straightforward, programming language-like approach
- **Component-Based Architecture**: Compose reusable components to build sophisticated agent systems
- **Comprehensive Observability**: Built-in logging, tracing, and metrics collection for all agent activities
- **Reproducible Execution**: Track and replay agent execution through a run context system
- **Extensible Node System**: Easily create custom node types to extend functionality
- **Resource Management**: Flexible management of AI model resources and credentials

## Core Concepts

### Components

DAD is built around the concept of components that encapsulate specific behaviors:

- **Flows**: Sequences of nodes that process data in a directed manner
- **Agents**: Higher-level components that coordinate multiple flows
- **Nodes**: Individual execution units that perform specific operations

### Execution Model

The execution follows a hierarchical structure:

1. Components (Agents or Flows) define the overall structure
2. Nodes within components perform specific tasks
3. A RunContext manages the execution environment
4. Tracing, logging, and metrics provide visibility into execution

### Resource Management

DAD provides a flexible system for managing AI model resources and API credentials, making it easier to work with different LLM providers and models.

## Basic Example

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

This example defines a simple flow with a single AI model node that uses Claude 3.5 Haiku to answer a question.

## Next Steps

The following sections of the documentation will provide in-depth explanations of the DAD architecture, components, and how to use them effectively for your AI agent applications.
