# Dhenara Agent DSL (DAD) - CLI Architecture

## Overview

The Dhenara Agent DSL Command Line Interface (CLI) provides a robust and extensible system for interacting with DAD agents and projects. It offers commands for creating, running, deploying, and managing agent outputs. This document details the architecture of the CLI system and how to use or extend it.

## Core Architecture

The DAD CLI is built using [Click](https://click.palletsprojects.com/), a Python package for creating beautiful command line interfaces. The architecture follows a modular design pattern with several key components:

### Main Entry Point

The CLI system is initialized through a main entry point that dynamically discovers and loads command modules:

```python
@click.group()
def cli():
    """Dhenara Agent DSL (DAD) CLI."""
    pass

# Dynamically import all command modules
def load_commands():
    commands_path = Path(__file__).parent / "commands"
    observability_commands_path = Path(__file__).parent.parent / "agent" / "observability" / "cli"

    # Load regular commands
    for _, name, _is_pkg in pkgutil.iter_modules([str(commands_path)]):
        if not name.startswith("_"):  # Skip private modules
            module = importlib.import_module(f"dhenara.cli.commands.{name}")
            if hasattr(module, "register"):
                module.register(cli)

    # Load observability commands
    for _, name, _is_pkg in pkgutil.iter_modules([str(observability_commands_path)]):
        if not name.startswith("_"):  # Skip private modules
            module = importlib.import_module(f"dhenara.agent.observability.cli.{name}")
            if hasattr(module, "register"):
                module.register(cli)
```

### Command Registration Pattern

Each command module implements a `register` function that adds its commands to the main CLI group:

```python
def register(cli):
    cli.add_command(my_command)

@click.command("my-command")
@click.argument("argument")
@click.option("--option", help="Description of the option")
def my_command(argument, option):
    """Command description that appears in the help text."""
    # Command implementation
```

This pattern allows for modular addition of new commands without modifying the core CLI code.

## Command Structure

The DAD CLI organizes commands into logical groups based on functionality:

### Project Initialization

- `startproject`: Creates a new DAD project with the necessary directory structure and configuration files

### Agent Management

- `create agent`: Creates a new agent within an existing project
- `run agent`: Executes an agent in an isolated environment

### Deployment

- `deploy`: Deploys an agent or application to various environments (dev, staging, prod)

### Output Management

- `outputs list`: Lists all available run outputs
- `outputs compare`: Compares outputs from different runs
- `outputs checkout`: Checks out a specific run output

### Observability

- Various commands for viewing and analyzing traces, logs, and metrics

## Command Implementation

### Run Agent Command

The `run agent` command demonstrates the typical pattern for implementing complex commands:

```python
@run.command("agent")
@click.argument("identifier")
@click.option("--project-root", default=None, help="Project repo root")
@click.option(
    "--previous-run-id",
    default=None,
    help="ID of a previous run to use as a base for this run",
)
@click.option(
    "--start-path",
    default=None,
    help="Hierarchical path to start execution from (e.g., 'agent_id/flow_id/node_id')",
)
def run_agent(identifier, project_root, previous_run_id, start_path):
    """Run an agent with the specified identifier."""
    # Uses asyncio to run the async implementation
    asyncio.run(
        _run_agent(
            identifier=identifier,
            project_root=project_root,
            previous_run_id=previous_run_id,
            start_hierarchy_path=start_path,
        )
    )
```

The pattern typically includes:
1. Command declaration with Click decorators
2. Arguments and options with help text
3. Synchrounous wrapper function that calls into async implementation
4. Detailed implementation in a separate async function

## Runner Architecture

The runner system is a crucial part of the CLI architecture that handles agent execution:

```python
async def _run_agent(identifier, project_root, previous_run_id, start_hierarchy_path):
    # Find project root
    if not project_root:
        project_root = find_project_root()
    if not project_root:
        click.echo("Error: Not in a Dhenara project directory.")
        return

    # Load agent runner
    runner = load_runner_module(project_root, identifier)

    # Setup and execute
    runner.setup_run(
        previous_run_id=previous_run_id,
        start_hierarchy_path=start_hierarchy_path,
    )

    # Run agent in isolated execution context
    async with IsolatedExecution(runner.run_context) as executor:
        _result = await executor.run(runner=runner)
```

Key aspects of the runner architecture:

1. **Project Discovery**: Automatically finds the project root directory
2. **Module Loading**: Dynamically imports the runner module for the specified agent
3. **Run Context Setup**: Configures the execution environment with parameters
4. **Isolated Execution**: Executes the agent in an isolated environment to prevent interference
5. **Result Reporting**: Displays execution results and directs the user to outputs

## Project Structure

The DAD CLI expects projects to follow a specific structure:

```
project-name/
├─ .dhenara/             # Dhenara configuration directory
│  ├─ config.yaml        # Project configuration
│  └─ credentials/       # Credentials for AI models and services
├─ src/                  # Source code directory
│  ├─ agents/            # Agent definitions
│  │  └─ my_agent/       # Individual agent directory
│  │     ├─ agent.py     # Main agent definition
│  │     ├─ flow.py      # Agent flow definitions
│  │     └─ inputs/      # Agent input handlers
│  │        └─ handler.py
│  ├─ common/            # Shared code
│  │  └─ prompts/        # Reusable prompts
│  └─ runners/           # Agent runners
│     ├─ defs.py         # Common runner definitions
│     └─ my_agent.py     # Agent-specific runner
└─ README.md             # Project documentation
```

This structure is automatically created by the `startproject` command and expanded by the `create agent` command.

## Templates System

The CLI utilizes a templates system for generating boilerplate code when creating projects and agents:

```python
template_dir = Path(__file__).parent.parent / "templates" / "agent"
runner_template_dir = Path(__file__).parent.parent / "templates" / "runner"

# Copy and customize templates
for template_file in template_dir.glob("*"):
    if template_file.is_file():
        target_file = agent_dir / template_file.name
        with open(template_file) as src, open(target_file, "w") as dst:
            content = src.read()
            # Replace placeholders
            content = content.replace("{{agent_identifier}}", agent_identifier)
            content = content.replace("{{agent_name}}", name)
            dst.write(content)
```

The templates include:

1. **Agent Templates**: Basic agent structure with flow definitions and input handlers
2. **Runner Templates**: Runner configurations for executing agents

## Extending the CLI

The modular design makes extending the CLI straightforward:

1. Create a new Python module in the `dhenara/cli/commands/` directory
2. Implement a `register` function that adds your commands to the CLI
3. Define your commands using Click decorators

Example of adding a new command:

```python
# dhenara/cli/commands/my_feature.py
import click

def register(cli):
    cli.add_command(my_feature)

@click.group("my-feature")
def my_feature():
    """My feature description."""
    pass

@my_feature.command("action")
@click.argument("name")
def my_action(name):
    """Perform an action with my feature."""
    click.echo(f"Performing action with {name}")
```

## Best Practices

1. **Consistent Command Structure**: Follow the established pattern of command registration
2. **Descriptive Help Text**: Provide clear, concise help for all commands and options
3. **Isolated Async Execution**: Use the `IsolatedExecution` context for running agents
4. **Error Handling**: Implement proper error handling and reporting
5. **User Feedback**: Provide clear feedback about command progress and results

## Conclusion

The DAD CLI architecture offers a flexible, extensible system for interacting with Dhenara Agent DSL. Its modular design makes it easy to add new commands and functionality while maintaining a consistent user experience. By following the established patterns and best practices, you can leverage the full power of DAD through its command-line interface.