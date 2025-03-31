import importlib
import pkgutil
import sys
from pathlib import Path

import click


# This will be the main entry point for all CLI commands
@click.group()
def cli():
    """Dhenara AI development toolkit."""
    pass


# Dynamically import all command modules
def load_commands():
    commands_path = Path(__file__).parent / "commands"
    observability_commands_path = Path(__file__).parent.parent / "agent" / "observability" / "cli"

    for _, name, _is_pkg in pkgutil.iter_modules([str(commands_path)]):
        if not name.startswith("_"):  # Skip private modules
            module = importlib.import_module(f"dhenara.cli.commands.{name}")
            if hasattr(module, "register"):
                module.register(cli)

    for _, name, _is_pkg in pkgutil.iter_modules([str(observability_commands_path)]):
        if not name.startswith("_"):  # Skip private modules
            module = importlib.import_module(f"dhenara.agent.observability.cli.{name}")
            if hasattr(module, "register"):
                module.register(cli)


# Load all commands
load_commands()


def main():
    """Run the CLI with command line arguments."""
    return cli(sys.argv[1:])


if __name__ == "__main__":
    main()
