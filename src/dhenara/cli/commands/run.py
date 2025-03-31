import asyncio
import importlib
import logging
from pathlib import Path

import click

from dhenara.agent.run import IsolatedExecution
from dhenara.agent.shared.utils import find_project_root

from ._print_utils import print_error_summary, print_run_summary

logger = logging.getLogger(__name__)


def register(cli):
    cli.add_command(run)


@click.group(name="run")
def run():
    """Create new Dhenara components."""
    pass


@run.command("agent")
@click.argument("identifier")
@click.option("--project-root", default=None, help="Project repo root")
@click.option("--run-root", default=None, help="Run dir root. Default is `runs`")
@click.option(
    "--run-id",
    default=None,
    help="Custom run ID . Defaults is <agent_identifier>_<timestamp>_<uid>",
)
def run_agent(
    identifier,
    project_root,
    run_root,
    run_id,
):
    """Run an agent with the specified inputs.

    NAME is the name of the agent.
    """
    asyncio.run(
        _run_agent(
            identifier,
            project_root,
            run_root,
            run_id,
        )
    )


async def _run_agent(
    identifier,
    project_root,
    run_root,
    run_id,
):
    """Async implementation of run_agent."""
    # Find project root
    if not project_root:
        project_root = find_project_root()

    if not project_root:
        click.echo("Error: Not in a Dhenara project directory.")
        return

    # Load agent
    agent_module, run_ctx = load_agent_module(project_root, f"agents/{identifier}")
    if not (agent_module and run_ctx):
        raise ValueError("Failed to get agent module and run context")

    try:
        # Run agent in a subprocess for isolation
        async with IsolatedExecution(run_ctx) as executor:
            _result = await executor.run(
                agent_module=agent_module,
                run_context=run_ctx,
            )

        print(f"Agent run completed successfully. Run ID: {run_ctx.run_id}")
        print_run_summary(run_ctx)

        # View the traces in the dashboard if the file exists
        if run_ctx.trace_file.exists():
            # Launch the dashboard if traces were generated
            from dhenara.agent.observability.cli import view_trace_in_console

            print("Launching trace dashboard...")
            view_trace_in_console(file=run_ctx.trace_file)
            # run_dashboard(str(run_ctx.trace_file))

    except Exception as e:
        logger.exception(f"Error running agent {identifier}: {e}")
        run_ctx.metadata["error"] = str(e)
        run_ctx.complete_run(status="failed")
        print_error_summary(str(e))


def load_agent_module(project_root: Path, agent_dir_path: str):
    """Load agent module from the specified path."""
    try:
        # Add current directory to path
        import sys

        sys.path.append(str(project_root))

        # Convert file path notation to module notation
        _path = f"{agent_dir_path}/agent_run"
        module_path = _path.replace("/", ".")

        # Import agent from path
        run_module = importlib.import_module(module_path)
        return run_module.agent, run_module.run_context

    except ImportError as e:
        logger.error(f"Failed to import agent from project_root {project_root} path {agent_dir_path}: {e}")
    except AttributeError as e:
        logger.error(
            f"Failed to find agent definition in module project_root {project_root} path {agent_dir_path}: {e}"
        )
