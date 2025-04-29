# Dhenara Agent DSL (DAD) - Run System

## Run System Overview

The run system in DAD is responsible for managing execution contexts, environment setup, and artifact handling. It provides a structured approach to executing DAD components while maintaining isolation, reproducibility, and observability.

## Core Run System Components

### RunContext

The `RunContext` is the central component of the run system. It manages the execution environment, including:

- Run directories and IDs
- Input and output artifacts
- Observability configuration
- Resource management
- Event handling

```python
from dhenara.agent.run import RunContext
from pathlib import Path

# Create a run context
run_context = RunContext(
    root_component_id="my_agent",  # ID of the root component being executed
    project_root=Path("/path/to/project"),  # Project root directory
    run_root=Path("/path/to/project/runs"),  # Where run artifacts are stored
    observability_settings=my_observability_settings,  # Optional custom settings
)

# Setup the run (creates directories, initializes observability, etc.)
run_context.setup_run(run_id_prefix="test")
```

### RunEnvParams

The `RunEnvParams` class encapsulates the essential parameters for a run:

```python
from dhenara.agent.types.data import RunEnvParams

env_params = RunEnvParams(
    run_id="run_20231015_123456",
    run_dir="/path/to/project/runs/run_20231015_123456",
    run_root="/path/to/project/runs",
    trace_dir="/path/to/project/runs/run_20231015_123456/.trace",
    outcome_repo_dir="/path/to/project/runs/outcome/project_name",
)
```

### IsolatedExecution

The `IsolatedExecution` class provides a context manager for isolated execution environments:

```python
from dhenara.agent.run import IsolatedExecution

async with IsolatedExecution(run_context) as execution:
    # Operations within this block run in an isolated environment
    result = await execution.run(runner)
```

This ensures that each run has its own isolated environment, preventing interference between runs.

## Run Directory Structure

A typical run directory structure looks like this:

```
project_root/
├─ runs/
│  ├─ run_20231015_123456/  # Individual run directory
│  │  ├─ .trace/           # Observability data
│  │  │  ├─ trace.jsonl
│  │  │  ├─ metrics.jsonl
│  │  │  ├─ logs.jsonl
│  │  │  └─ dad_metadata.json
│  │  ├─ static_inputs/    # Input data
│  │  ├─ node1/            # Node-specific directories
│  │  ├─ node2/
│  │  └─ ...
│  ├─ outcome/             # Outcome repository
│  │  └─ project_name/     # Git repository for outcomes
```

## Run Lifecycle

1. **Initialization**: Create a `RunContext` with appropriate parameters
2. **Setup**: Call `setup_run()` to create directories and initialize systems
3. **Execution**: Runner uses the context to execute components
4. **Artifact Management**: Results and intermediate data stored in run directory
5. **Completion**: Call `complete_run()` to finalize and record completion status

```python
try:
    # Initialize and setup
    run_context = RunContext(root_component_id="my_agent", project_root=Path("."))
    run_context.setup_run()
    
    # Execute
    runner = AgentRunner(my_agent, run_context)
    result = await runner.run()
    
    # Complete successfully
    run_context.complete_run(status="completed")
    
    return result
except Exception as e:
    # Handle failure
    run_context.complete_run(status="failed", error_msg=str(e))
    raise
```

## Re-runs and Continuations

DAD supports re-running previous executions or continuing from specific points:

```python
# Create a run context for a re-run
run_context = RunContext(
    root_component_id="my_agent",
    project_root=Path("."),
    previous_run_id="run_20231015_123456",  # ID of the previous run
    start_hierarchy_path="agent.flow1.node3"  # Continue from this node
)

# Setup the run with re-run parameters
run_context.setup_run()
```

This enables debugging, experimentation, and incremental development of agent workflows.

## Static Inputs

DAD supports providing static inputs to nodes:

```python
# Register static input for a specific node
run_context.register_node_static_input(
    "my_node_id",
    MyNodeInput(param1="value1", param2="value2")
)

# Or load static inputs from JSON
run_context.read_static_inputs()  # Reads from static_inputs.json
```

## Event Handling

The run system includes an event bus for dynamic interactions:

```python
# Register an input handler
async def my_input_handler(event):
    if event.node_id == "some_node":
        event.input = SomeNodeInput(value="dynamic_value")
        event.handled = True

run_context.register_node_input_handler(my_input_handler)
```

## Resource Configuration

The run system manages resources through a resource registry:

```python
# Get resource configuration
resource_config = run_context.get_resource_config("my_profile")

# Use in component definition
ai_node = AIModelNode(
    resources=resource_config.get_model("claude-3-5-sonnet"),
    # Other settings...
)
```

This system allows for flexible resource management across different environments and configurations.
