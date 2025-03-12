import os
import subprocess
from pathlib import Path

import click
import yaml

# Import the internal functions directly
from .create import _create_agent, _create_flow


def register(cli):
    cli.add_command(startproject)


@click.command("startproject")
@click.option("--name", prompt="Project name", help="Name of the new project")
# @click.option("--description", default="", help="Description of the project")
@click.option("--agent", default="my_agent", help="Name of the initial agent")
@click.option("--flow", default="my_flow", help="Name of the initial flow")
@click.option("--git/--no-git", default=True, help="Initialize a git repository")
def startproject(name, agent, flow, git):
    """Create a new project with predefined structure including initial agent and flow."""
    # Convert to valid package name
    package_name = name.lower().replace(" ", "_").replace("-", "_")

    # Create project directory
    project_dir = Path(os.getcwd()) / package_name
    if project_dir.exists():
        click.echo(f"Error: Directory {project_dir} already exists!")
        return

    project_dir.mkdir()
    click.echo(f"Creating new project '{name}' in {project_dir}")

    # Create basic project structure
    src_dir = project_dir / "src"
    src_dir.mkdir()
    agents_dir = src_dir / "agents"
    agents_dir.mkdir()

    # Create __init__.py files
    with open(project_dir / "__init__.py", "w") as f:
        f.write(f'"""Dhenara project: {name}"""')

    with open(src_dir / "__init__.py", "w") as f:
        f.write("")

    with open(agents_dir / "__init__.py", "w") as f:
        f.write("")

    # Create project config.yaml
    config = {
        "name": name,
        "description": "",
        "version": "0.0.1",
        "author": os.environ.get("USER", "dhenara-user"),
    }

    with open(project_dir / "config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # Create README.md
    with open(project_dir / "README.md", "w") as f:
        f.write(f"# {name}\n\n## Getting Started\n\n```python\nfrom {package_name}.src.agents.{agent}.flows.{flow} import run_flow\n\nresult = run_flow(input_data)\n```")

    # Create initial agent and flow
    if agent:
        # Change to project directory
        old_cwd = os.getcwd()
        os.chdir(project_dir)

        try:
            # Create initial agent
            _create_agent(name=agent, description=f"Initial agent for {name}")

            # Create initial flow within agent
            if flow:
                _create_flow(name=flow, description=f"Initial flow for {agent} agent", agent=agent)

        finally:
            # Restore original working directory
            os.chdir(old_cwd)

    # Initialize git repository if requested
    if git:
        try:
            subprocess.run(["git", "init"], cwd=project_dir, check=True, stdout=subprocess.PIPE)
            with open(project_dir / ".gitignore", "w") as f:
                f.write("__pycache__/\n*.py[cod]\n*$py.class\n.env\n.venv\nenv/\nvenv/\n*.log\n.DS_Store")
            click.echo("Initialized git repository")
        except Exception as e:
            click.echo(f"Warning: Could not initialize git repository: {e}")

    click.echo(f"✅ Project '{name}' created successfully!")
    click.echo(f"To get started, cd into {package_name} and start developing!")
