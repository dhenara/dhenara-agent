import asyncio
import importlib
import logging
from pathlib import Path

import click

from dhenara.agent.run import IsolatedExecution, RunContext
from dhenara.agent.shared.utils import find_project_root

logger = logging.getLogger(__name__)

# Set logger level for a specific package
logging.getLogger("dhenara.agent").setLevel(logging.DEBUG)


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
@click.option(
    "--input_source_path",
    default=None,
    help=(
        "Input source path from where inputs will be copied to `<run_root>/input`. "
        "Default is `<project-root>/agents/<name>/input`"
    ),
)
def run_agent(
    identifier,
    project_root,
    run_root,
    run_id,
    input_source_path,
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
            input_source_path,
        )
    )


async def _run_agent(
    identifier,
    project_root,
    run_root,
    run_id,
    input_source_path,
):
    """Async implementation of run_agent."""
    # Find project root
    if not project_root:
        project_root = find_project_root()

    if not project_root:
        click.echo("Error: Not in a Dhenara project directory.")
        return

    # Create run context
    run_ctx = RunContext(
        project_root=project_root,
        agent_identifier=identifier,
        input_source_path=input_source_path,
        initial_inputs=None,
        run_root=run_root,
        run_id=run_id,
    )

    try:
        # Load agent
        agent_module = load_agent_module(project_root, f"agents/{identifier}/agent")
        if not agent_module:
            raise ValueError("Failed to get agent module")

        # Run agent in a subprocess for isolation
        async with IsolatedExecution(run_ctx) as executor:
            _result = await executor.run(
                agent_module=agent_module,
                run_context=run_ctx,
                initial_inputs=None,
            )

        click.echo(f"✅ Run completed successfully. Run ID: {run_ctx.run_id}")
        click.echo(f"   Output directory: {run_ctx.output_dir}")

    except Exception as e:
        run_ctx.metadata["error"] = str(e)
        run_ctx.complete_run(status="failed")
        click.echo(f"❌ Run failed: {e}")


def load_agent_module(project_root: Path, agent_path: str):
    """Load agent module from the specified path."""
    try:
        # Add current directory to path
        import sys

        sys.path.append(str(project_root))

        # Convert file path notation to module notation
        module_path = agent_path.replace("/", ".")

        # Import agent from path
        agent = importlib.import_module(module_path)
        return agent.agent

    except ImportError as e:
        logger.error(f"Failed to import agent from project_root {project_root} path {agent_path}: {e}")
    except AttributeError as e:
        logger.error(f"Failed to find agent definition in module project_root {project_root} path {agent_path}: {e}")
