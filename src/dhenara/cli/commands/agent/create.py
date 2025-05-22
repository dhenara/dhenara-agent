import os
from pathlib import Path

import click

from dhenara.agent.utils.shared import generate_identifier, is_project_dir, validate_name


@click.command(name="create")
@click.argument("name")
@click.option("--description", default="", help="Description of the agent")
def create_agent(name, description):
    """Create a new agent within the current project."""
    # Check if we're in a project directory
    if not is_project_dir(os.getcwd()):
        click.echo(click.style("Error: Must be run within a DAD project directory.", fg="red", bold=True))
        click.echo(click.style("Tip: Run 'dad startproject' to create a new project first.", fg="blue"))
        return False

    # Validate the agent name
    if not validate_name(name):
        click.echo(
            click.style(
                "Error: Invalid agent name. Please use alphanumeric characters, spaces, or hyphens.",
                fg="red",
                bold=True,
            )
        )
        return False

    _create_agent(name, description)


def _create_agent(name, description):
    """Internal function to create an agent."""
    # Generate valid agent identifier
    agent_identifier = generate_identifier(name)

    # Get current directory
    current_dir = Path(os.getcwd())

    # Create agents directory if it doesn't exist
    agents_dir = current_dir / "src" / "agents"
    runners_dir = current_dir / "src" / "runners"
    if not agents_dir.exists():
        agents_dir.mkdir()
        with open(agents_dir / "__init__.py", "w") as f:
            f.write("")

    # Create agent directory
    agent_dir = agents_dir / agent_identifier
    if agent_dir.exists():
        click.echo(click.style(f"Error: Agent {agent_identifier} already exists!", fg="red", bold=True))
        return False

    agent_dir.mkdir()

    # Create agent __init__.py
    with open(agent_dir / "__init__.py", "w") as f:
        f.write("")
        # f.write(f'"""Dhenara agent: {name}"""\n\nfrom .agent import Agent\n')

    # Get template directory path
    template_dir = Path(__file__).parent.parent.parent / "templates" / "agent"
    runner_template_dir = Path(__file__).parent.parent.parent / "templates" / "runner"

    if not template_dir:
        click.echo(click.style("Error: Could not find template directory.", fg="red", bold=True))
        return False

    try:
        # Runner file
        runner_src = runner_template_dir / "runner.py"
        runner_dest = runners_dir / f"{agent_identifier}.py"
        with open(runner_src) as src, open(runner_dest, "w") as dst:
            content = src.read()
            # Replace placeholders
            content = content.replace("from src.agents.my_agent.", f"from src.agents.{agent_identifier}.")
            content = content.replace("my_agent", agent_identifier)
            dst.write(content)

        # Agent dir
        for template_file in template_dir.glob("*"):
            if template_file.is_file():
                target_file = agent_dir / template_file.name
                with open(template_file) as src, open(target_file, "w") as dst:
                    content = src.read()
                    # Replace placeholders
                    content = content.replace("{{agent_identifier}}", agent_identifier)
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
                            content = content.replace("{{agent_identifier}}", agent_identifier)
                            content = content.replace("{{agent_name}}", name)
                            content = content.replace("{{agent_name}}", name)
                            content = content.replace("{{agent_description}}", description)
                            dst.write(content)
    except Exception as e:
        click.echo(click.style(f"Error copying templates: {e}", fg="red"))
        # Attempt to clean up on failure
        import shutil

        try:
            shutil.rmtree(agent_dir)
        except:
            pass
        return False

    click.echo(click.style(f"✅ Agent '{name}' created successfully!", fg="green", bold=True))
    click.echo(f"  - Identifier: {agent_identifier}")
    click.echo(f"  - Location: {agent_dir}")
    click.echo(f"  - Command to run:  dad agent run {agent_identifier}")

    return True
