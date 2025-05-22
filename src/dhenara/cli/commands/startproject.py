import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import click
import yaml

from dhenara.agent.utils.shared import generate_identifier, validate_name
from dhenara.ai.types.resource import ResourceConfig

from .agent.create import _create_agent


def register(cli):
    cli.add_command(startproject)


@click.command("startproject")
@click.argument("project_name")
@click.argument("agent_name", required=False)
@click.option("--description", default="", help="Project description")
@click.option("--git/--no-git", default=True, help="Initialize git repositories")
def startproject(project_name, agent_name, description, git):
    """Create a DAD project with folder structure.

    PROJECT_NAME is the name of the new project.
    AGENT_NAME (optional) is the name of the initial agent to create.
    """
    # Validate the project name
    if not validate_name(project_name):
        click.echo(
            click.style(
                "Error: Invalid project name. Please use alphanumeric characters, spaces, or hyphens.",
                fg="red",
                bold=True,
            )
        )
        return

    # Generate project identifier (with hyphens for directory name)
    project_identifier = generate_identifier(project_name, use_hyphens=False)

    # Create project directory
    project_dir = Path(os.getcwd()) / project_identifier
    if project_dir.exists():
        click.echo(click.style(f"Error: Directory {project_dir} already exists!", fg="red", bold=True))
        return

    # Create directory structure
    project_dir.mkdir()
    dirs = [
        ".dhenara",
        ".dhenara/.secrets",
        "src/agents",
        "src/runners",
        # "src/common/prompts",
        # "src/tests",
    ]

    for dir_path in dirs:
        (project_dir / dir_path).mkdir(parents=True, exist_ok=True)

    # Create base configuration files
    config = {
        "project": {
            "name": project_name,
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

    # Create credentials.yaml
    _credentials_path = project_dir / ".dhenara" / ".secrets" / ".credentials.yaml"
    ResourceConfig.create_credentials_template(str(_credentials_path))

    # Create README
    with open(project_dir / "README.md", "w") as f:
        f.write(f"# {project_name}\n\n{description}\n\n## Getting Started\n\n...")

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
.dhenara/.secrets/

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

    # Copy initial files in runners dir
    runnner_template_dirs = Path(__file__).parent.parent / "templates" / "runner"
    shutil.copy(runnner_template_dirs / "__init__.py", project_dir / "src" / "runners")
    shutil.copy(runnner_template_dirs / "defs.py", project_dir / "src" / "runners")

    # Change to the project directory to create an initial agent
    os.chdir(project_dir)

    # Create an initial agent - either the specified agent_name or project_name if not specified
    validated_agent_name = None
    if agent_name:
        if not validate_name(agent_name):
            click.echo(
                click.style(
                    "Error: Invalid agent name. Please use alphanumeric characters, spaces, or hyphens.",
                    fg="red",
                    bold=True,
                )
            )
            # Continue with project creation but without agent
        else:
            validated_agent_name = agent_name
    else:
        # validated_agent_name = project_name
        pass

    if validated_agent_name:
        _create_agent(validated_agent_name, description)

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
                if dir_path in [".dhenara/.secrets"]:
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
    click.echo(click.style(f"✅ Project '{project_name}' created successfully!", fg="green", bold=True))
    click.echo(f"  - Project identifier: {project_identifier}")
    click.echo(f"  - Location: {project_dir}")

    # Show agent creation success message
    if validated_agent_name:
        click.echo(f"  - Initial agent created: {validated_agent_name}")

    click.echo("\nNext steps:")
    click.echo(f"  1. cd {project_identifier}")
    # click.echo("  2. Initialize your environment (poetry install, etc.)")

    if validated_agent_name:
        click.echo(f"  2. dad agent run {validated_agent_name}")
        click.echo("  3. dad agent create <agent_name> (To create additional agents)")
    else:
        click.echo("  2. dad agent create <agent_name> ")
