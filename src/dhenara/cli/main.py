import importlib
import pkgutil
import sys
import warnings
from pathlib import Path

import click


# This will be the main entry point for all CLI commands
@click.group()
@click.version_option(package_name="dhenara.agent")
def cli():
    """Dhenara Agent DSL (DAD) development toolkit."""
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

    # Try to load Pro commands
    try:
        from dhenara.agent.pro.cli import register_pro_commands  # type: ignore

        register_pro_commands(cli)
    except ImportError:
        # Pro package not installed
        pass


# Load all commands
load_commands()


def main():
    """Run the CLI with command line arguments."""

    if "dhenara" in sys.argv[0]:
        warnings.warn(
            "\n\n'dhenara' command is deprecated and will be removed in version 0.3.X. Please use 'dad' instead.\n",
            DeprecationWarning,
            stacklevel=2,
        )

    return cli(sys.argv[1:])


if __name__ == "__main__":
    main()
