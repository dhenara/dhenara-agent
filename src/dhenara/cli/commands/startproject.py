import os
import subprocess
from datetime import datetime
from pathlib import Path

import click
import yaml

from dhenara.agent.shared.utils import generate_identifier, validate_name

from .create import _create_agent


def register(cli):
    cli.add_command(startproject)


@click.command("startproject")
@click.argument("name")
@click.option("--description", default="", help="Project description")
@click.option("--git/--no-git", default=True, help="Initialize git repositories")
def startproject(name, description, git):
    """Create a new agent project with a professional structure.

    NAME is the name of the new project.
    """
    # Validate the project name
    if not validate_name(name):
        click.echo(
            click.style(
                "Error: Invalid project name. Please use alphanumeric characters, spaces, or hyphens.",
                fg="red",
                bold=True,
            )
        )
        return

    # Generate project identifier (with hyphens for directory name)
    project_identifier = generate_identifier(name, use_hyphens=True)

    # Create project directory
    project_dir = Path(os.getcwd()) / project_identifier
    if project_dir.exists():
        click.echo(click.style(f"Error: Directory {project_dir} already exists!", fg="red", bold=True))
        return

    # Create directory structure
    project_dir.mkdir()
    dirs = [
        ".dhenara",
        ".dhenara/credentials",
        "agents",
        "common/prompts",
        # "common/tools",
        # "data",
        # "experiments",
        # "scripts",
        # "tests",
    ]

    for dir_path in dirs:
        (project_dir / dir_path).mkdir(parents=True, exist_ok=True)

    # Create base configuration files
    config = {
        "project": {
            "name": name,
            "identifier": project_identifier,
            "description": description,
            "version": "0.0.1",
        },
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
        "settings": {
            # Default settings can be added here
        },
    }

    # Use a proper YAML dumper with good formatting
    with open(project_dir / ".dhenara" / "config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # Create README
    with open(project_dir / "README.md", "w") as f:
        f.write(f"# {name}\n\n{description}\n\n## Getting Started\n\n...")

    # Create pyproject.toml
    with open(project_dir / "pyproject.toml", "w") as f:
        f.write(f"""[tool.poetry]
name = "{project_identifier}"
version = "0.0.1"
description = "{description}"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
dhenara = "^0.1.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
""")

    # Create .gitignore
    with open(project_dir / ".gitignore", "w") as f:
        f.write("""# Python
__pycache__/
*.py[cod]
*$py.class
.env
.venv
env/
venv/
ENV/

# Credentials
.dhenara/credentials/

# Agent Runs
runs/

# Logs
*.log

# OS specific
.DS_Store

# IDEs
.idea/
.vscode/
""")

    # Change to the project directory to create an initial agent
    os.chdir(project_dir)

    # Create an initial agent with the same name as the project
    _create_agent(name, description)

    # Initialize project git repository
    if git:
        try:
            click.echo("Initializing Git.")
            # Main project repo
            subprocess.run(["git", "init", "-b", "main"], cwd=project_dir, check=True, stdout=subprocess.PIPE)

            # Add files and directories individually
            subprocess.run(["git", "add", ".gitignore"], cwd=project_dir, check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "add", ".dhenara"], cwd=project_dir, check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "add", "README.md"], cwd=project_dir, check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "add", "pyproject.toml"], cwd=project_dir, check=True, stdout=subprocess.PIPE)

            # Add all directories individually
            for dir_path in dirs:
                if dir_path in [".dhenara/credentials"]:
                    continue
                subprocess.run(["git", "add", dir_path], cwd=project_dir, check=True, stdout=subprocess.PIPE)

            ## Commit the initial structure
            # subprocess.run(
            #    ["git", "commit", "-m", "Initial project structure"],
            #    cwd=project_dir,
            #    check=True,
            #    stdout=subprocess.PIPE,
            # )
        except subprocess.SubprocessError as e:
            click.echo(click.style(f"Warning: Failed to initialize git repositories: {e}", fg="yellow"))
            click.echo("You can manually initialize Git later if needed.")

    # Print success message with more details
    click.echo(click.style(f"✅ Project '{name}' created successfully!", fg="green", bold=True))
    click.echo(f"  - Project identifier: {project_identifier}")
    click.echo(f"  - Location: {project_dir}")
    click.echo(f"  - Initial agent created: {name}")
    click.echo("\nNext steps:")
    click.echo("  1. cd " + project_identifier)
    click.echo("  2. Initialize your environment (poetry install, etc.)")
    click.echo("  3. Run 'dhenara create agent' to create additional agents")
