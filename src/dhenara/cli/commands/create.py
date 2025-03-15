import os
from pathlib import Path

import click

from dhenara.cli.utils.cli_utils import is_project_dir


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
    # Check if we're in a project directory
    if not is_project_dir(os.getcwd()):
        click.echo(click.style("Error: Must be run within a Dhenara project directory.", fg="red", bold=True))
        click.echo(click.style("Tip: Run 'dhenara startproject' to create a new project first.", fg="blue"))
        return False

    _create_agent(name, description)


def _create_agent(name, description):
    """Internal function to create an agent."""
    # Convert to valid directory name
    agent_name = name.lower().replace(" ", "_").replace("-", "_")

    # Get current directory
    current_dir = Path(os.getcwd())

    # Create agents directory if it doesn't exist
    agents_dir = current_dir / "agents"
    if not agents_dir.exists():
        agents_dir.mkdir()
        with open(agents_dir / "__init__.py", "w") as f:
            f.write("")

    # Create agent directory
    agent_dir = agents_dir / agent_name
    if agent_dir.exists():
        click.echo(click.style(f"Error: Agent {agent_name} already exists!", fg="red", bold=True))
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

    try:
        for template_file in template_dir.glob("*"):
            if template_file.is_file():
                target_file = agent_dir / template_file.name
                with open(template_file) as src, open(target_file, "w") as dst:
                    content = src.read()
                    # Replace placeholders
                    content = content.replace("{{agent_name}}", name)
                    content = content.replace("{{agent_description}}", description)
                    dst.write(content)
            elif template_file.is_dir() and template_file.name != "__pycache__":
                # Copy subdirectories (except __pycache__)
                target_dir = agent_dir / template_file.name
                if not target_dir.exists():
                    target_dir.mkdir(parents=True)

                for sub_file in template_file.glob("**/*"):
                    if sub_file.is_file():
                        rel_path = sub_file.relative_to(template_file)
                        dst_file = target_dir / rel_path
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(sub_file) as src, open(dst_file, "w") as dst:
                            content = src.read()
                            # Replace placeholders
                            content = content.replace("{{agent_name}}", name)
                            content = content.replace("{{agent_description}}", description)
                            dst.write(content)
    except Exception as e:
        click.echo(click.style(f"Error copying templates: {e}", fg="red"))

    ## Create agent config
    # config = {
    #    "name": name,
    #    "description": description,
    #    "version": "0.0.1",
    # }

    # with open(agent_dir / "config.yaml", "w") as f:
    #    yaml.dump(config, f, default_flow_style=False)

    click.echo(click.style(f"✅ Agent '{name}' created successfully!", fg="green", bold=True))
    return True
