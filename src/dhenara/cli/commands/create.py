import os
from pathlib import Path

import click
import yaml


def register(cli):
    cli.add_command(create)


@click.group(name="create")
def create():
    """Create new Dhenara components."""
    pass


@create.command("agent")
@click.option("--name", prompt="Agent name", help="Name of the new agent")
@click.option("--description", default="", help="Description of the agent")
def create_agent(name, description):
    """Create a new agent within the current project."""
    _create_agent(name, description)


def _create_agent(name, description):
    """Internal function to create an agent."""
    # Convert to valid directory name
    agent_name = name.lower().replace(" ", "_").replace("-", "_")

    # Get current directory
    current_dir = Path(os.getcwd())

    # Check if we're in a Dhenara project (should have src directory)
    src_dir = current_dir / "src"
    if not src_dir.exists():
        src_dir = current_dir
        click.echo("Warning: src directory not found, creating agent in current directory")

    # Create agents directory if it doesn't exist
    agents_dir = src_dir / "agents"
    if not agents_dir.exists():
        agents_dir.mkdir()
        with open(agents_dir / "__init__.py", "w") as f:
            f.write("")

    # Create agent directory
    agent_dir = agents_dir / agent_name
    if agent_dir.exists():
        click.echo(f"Error: Agent {agent_name} already exists!")
        return False

    agent_dir.mkdir()

    # Create agent __init__.py
    with open(agent_dir / "__init__.py", "w") as f:
        f.write(f'"""Dhenara agent: {name}"""\n\nfrom .agent import Agent\n')

    # Get template directory path
    # Look for templates in several plausible locations
    possible_template_dirs = [
        Path(__file__).parent.parent / "templates" / "agent",
        Path(__file__).parent / "templates" / "agent",
        Path.home() / ".dhenara" / "templates" / "agent",
    ]

    template_dir = None
    for path in possible_template_dirs:
        if path.exists():
            template_dir = path
            break

    if template_dir is None:
        # Create a basic agent file if no template is available
        click.echo("Warning: No agent template found, creating basic agent file")
        with open(agent_dir / "agent.py", "w") as f:
            f.write(f'''"""
{name} Agent

{description}
"""

class Agent:
    """Agent for {name}."""

    def __init__(self):
        """Initialize the agent."""
        self.name = "{name}"
        self.description = "{description}"

    def run(self, input_data=None):
        """Run the agent with the provided input."""
        return {{"result": "Agent execution complete", "input": input_data}}
''')
    else:
        # Create agent file from template
        agent_template = template_dir / "agent.py"
        if agent_template.exists():
            with open(agent_template) as f:
                template_content = f.read()

            template_content = template_content.replace("{{agent_name}}", name)
            template_content = template_content.replace("{{agent_description}}", description)

            with open(agent_dir / "agent.py", "w") as f:
                f.write(template_content)

    # Create flows directory
    flows_dir = agent_dir / "flows"
    flows_dir.mkdir()
    with open(flows_dir / "__init__.py", "w") as f:
        f.write("")

    # Create agent config
    config = {
        "name": name,
        "description": description,
        "version": "0.0.1",
    }

    with open(agent_dir / "config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    click.echo(f"✅ Agent '{name}' created successfully!")
    return True


@create.command("flow")
@click.option("--name", prompt="Flow name", help="Name of the new flow")
@click.option("--description", default="", help="Description of the flow")
@click.option("--agent", prompt="Agent name", help="Name of the agent this flow belongs to")
@click.option("--template", default="default", help="Template to use for the flow")
def create_flow(name, description, agent, template):
    """Create a new flow within an agent."""
    _create_flow(name, description, agent, template)


def _create_flow(name, description, agent, template="default"):
    """Internal function to create a flow."""
    # Convert to valid filenames
    flow_name = name.lower().replace(" ", "_").replace("-", "_")
    agent_name = agent.lower().replace(" ", "_").replace("-", "_")

    # Get current directory
    current_dir = Path(os.getcwd())

    # Check if we're in a Dhenara project (should have src directory)
    src_dir = current_dir / "src"
    if not src_dir.exists():
        src_dir = current_dir
        click.echo("Warning: src directory not found, assuming current directory is a project root")

    # Check if agents directory exists
    agents_dir = src_dir / "agents"
    if not agents_dir.exists():
        click.echo(f"Error: agents directory not found at {agents_dir}")
        return False

    # Check if the specified agent exists
    agent_dir = agents_dir / agent_name
    if not agent_dir.exists():
        click.echo(f"Error: Agent {agent_name} not found!")
        return False

    # Check/create flows directory within the agent
    flows_dir = agent_dir / "flows"
    if not flows_dir.exists():
        flows_dir.mkdir()
        with open(flows_dir / "__init__.py", "w") as f:
            f.write("")

    # Check if flow file already exists
    flow_file = flows_dir / f"{flow_name}.py"
    if flow_file.exists():
        click.echo(f"Error: Flow {flow_name}.py already exists in agent {agent_name}!")
        return False

    # Look for templates in several plausible locations
    possible_template_dirs = [
        Path(__file__).parent.parent / "templates" / "flow",
        Path(__file__).parent / "templates" / "flow",
        Path.home() / ".dhenara" / "templates" / "flow",
    ]

    template_dir = None
    for path in possible_template_dirs:
        if path.exists():
            template_dir = path
            break

    if template_dir is None:
        # Create a basic flow file if no template is available
        click.echo("Warning: No flow template found, creating basic flow file")
        with open(flow_file, "w") as f:
            f.write(f'''"""
{name} Flow

{description}
"""

def run_flow(input_data=None):
    """
    Execute the {name} flow.

    Args:
        input_data: Input data for the flow

    Returns:
        dict: Results of the flow execution
    """
    # Implement your flow logic here
    result = {{"status": "success", "message": "Flow executed", "data": input_data}}
    return result
''')
    else:
        # Try to find the specified template
        flow_template = template_dir / f"{template}.py"

        # If template doesn't exist, use default
        if not flow_template.exists():
            click.echo(f"Warning: Template {template}.py not found, using default.py")
            flow_template = template_dir / "default.py"

        # If even default doesn't exist, create a basic flow
        if not flow_template.exists():
            click.echo(f"Error: No flow templates found at {template_dir}, creating basic flow")
            with open(flow_file, "w") as f:
                f.write(f'''"""
{name} Flow

{description}
"""

def run_flow(input_data=None):
    """
    Execute the {name} flow.

    Args:
        input_data: Input data for the flow

    Returns:
        dict: Results of the flow execution
    """
    # Implement your flow logic here
    result = {{"status": "success", "message": "Flow executed", "data": input_data}}
    return result
''')
        else:
            # Copy and customize the template
            with open(flow_template) as f:
                template_content = f.read()

            # Replace template placeholders
            template_content = template_content.replace("{{flow_name}}", name)
            template_content = template_content.replace("{{flow_description}}", description)
            template_content = template_content.replace("{{agent_name}}", agent)

            # Write flow file
            with open(flow_file, "w") as f:
                f.write(template_content)

    # Update agent's flows config
    config_file = agent_dir / "config.yaml"
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = yaml.safe_load(f) or {}
        except Exception:
            config = {}
    else:
        config = {}

    # Add flow to config
    if "flows" not in config:
        config["flows"] = {}

    config["flows"][flow_name] = {
        "name": name,
        "description": description,
        "file": f"{flow_name}.py",
    }

    # Save config
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # Update __init__.py to expose the flow
    with open(flows_dir / "__init__.py", "a") as f:
        f.write(f"from .{flow_name} import run_flow as {flow_name}_run\n")

    click.echo(f"✅ Flow '{name}' created successfully in agent '{agent}'!")
    return True
