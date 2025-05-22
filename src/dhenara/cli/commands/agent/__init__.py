import click


@click.group(name="agent")
def agent_cli():
    """Agent-related commands."""
    pass


# Import subcommands and add them to the agent group
from .create import create_agent  # noqa: E402
from .run import run_agent  # noqa: E402

agent_cli.add_command(create_agent)
agent_cli.add_command(run_agent)


# Function to register this command group with the main CLI
def register(cli):
    cli.add_command(agent_cli)
