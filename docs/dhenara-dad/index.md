# Dhenara Agent DSL (DAD) Documentation

Welcome to the Dhenara Agent DSL (DAD) documentation. DAD is an open-source framework for creating and managing AI agents using a programming language-like approach. It is built on top of the `dhenara` Python package, providing a powerful domain-specific language for defining agent workflows.

## Table of Contents

1. [Introduction](01-introduction.md)
2. [Architecture](02-architecture.md)
3. [Components](03-components.md)
4. [Run System](04-run-system.md)
5. [Observability](05-observability.md)
6. [Resource Management](06-resource-management.md)
7. [Practical Guide](07-practical-guide.md)
8. [API Reference](08-api-reference.md)

## Quick Start

```python
from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    FlowDefinition,
)
from dhenara.ai.types import (
    ResourceConfigItem,
    Prompt,
)
from dhenara.agent.runner import FlowRunner
from dhenara.agent.run import RunContext
from pathlib import Path
import asyncio

# Define a simple flow
my_flow = FlowDefinition(root_id="simple_flow")

# Add an AI model node
my_flow.node(
    "assistant",
    AIModelNode(
        resources=ResourceConfigItem.with_model("claude-3-5-sonnet"),
        settings=AIModelNodeSettings(
            system_instructions=["You are a helpful assistant."],
            prompt=Prompt.with_dad_text("Answer the following question: $var{question}"),
        ),
    ),
)

# Create run context and runner
run_context = RunContext(
    root_component_id="simple_flow",
    project_root=Path("."),
)

# Register static input for the node
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import AIModelNodeInput
run_context.register_node_static_input(
    "assistant",
    AIModelNodeInput(prompt_variables={"question": "What is Dhenara Agent DSL?"})
)

# Run the flow
async def run_flow():
    run_context.setup_run()
    runner = FlowRunner(my_flow, run_context)
    result = await runner.run()
    return result

# Execute the flow
result = asyncio.run(run_flow())
print(f"Flow execution result: {result}")
```

## About Dhenara

Dhenara Inc is an early-stage GenAI startup with two key products:

- `dhenara`: An open-source Python package that simplifies LLM API calls across providers
- `dhenara-agent` (DAD): A new open-source project built on top of `dhenara` for creating and managing AI agents

DAD provides a programming language-like approach to defining and executing AI agent workflows, with robust observability and reproducibility features.

## Contributing

Contributions are welcome! Please see our contribution guidelines for details on how to help improve DAD.

## License

Dhenara Agent DSL is open-source software. Please see the LICENSE file for details.
