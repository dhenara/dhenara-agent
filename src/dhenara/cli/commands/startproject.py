import os
import subprocess
from datetime import datetime
from pathlib import Path

import click
import yaml

# Import the internal functions
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
    # Convert to valid directory name
    project_name = name.lower().replace(" ", "-").replace("_", "-")

    # Create project directory
    project_dir = Path(os.getcwd()) / project_name
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
        "common/tools",
        "data",
        "experiments",
        "runs/input",
        "runs/output",
        "scripts",
        "tests",
    ]

    for dir_path in dirs:
        (project_dir / dir_path).mkdir(parents=True, exist_ok=True)

    # Create base configuration files
    config = {
        "name": name,
        "description": description,
        "version": "0.0.1",
        "created_at": datetime.now().isoformat(),
    }

    with open(project_dir / ".dhenara" / "config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # Create README
    with open(project_dir / "README.md", "w") as f:
        f.write(f"# {name}\n\n{description}\n\n## Getting Started\n\n...")

    # Create pyproject.toml
    with open(project_dir / "pyproject.toml", "w") as f:
        f.write(f"""[tool.poetry]
name = "{project_name}"
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

    # Initialize git repositories
    if git:
        # Main project repo
        subprocess.run(["git", "init"], cwd=project_dir, check=True, stdout=subprocess.PIPE)

        # Initialize output directory as a separate git repo
        output_dir = project_dir / "runs" / "output"
        subprocess.run(["git", "init"], cwd=output_dir, check=True, stdout=subprocess.PIPE)

        # Create output .gitignore to allow tracking everything
        with open(output_dir / ".gitignore", "w") as f:
            f.write("# Track everything in this directory\n# This is an output repository\n")

    # Change to the project directory to create an initial agent
    os.chdir(project_dir)

    # Create an initial agent with the same name as the project
    _create_agent(name, description)

    click.echo(click.style(f"✅ Project '{name}' created successfully!", fg="green", bold=True))
