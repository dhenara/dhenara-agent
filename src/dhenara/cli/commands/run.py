import asyncio
import importlib
import json
import logging
from pathlib import Path

import click

from dhenara.agent.run import IsolatedExecution, RunContext
from dhenara.cli.utils.cli_utils import find_project_root

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
@click.argument("name")
@click.option("--project-root", default=None, help="Project repo root")
@click.option("--run-root", default=None, help="Run dir root. Default is `runs`")
@click.option("--input-file", default=None, help="Path to input JSON file")
@click.option(
    "--input-dir",
    default=None,
    help="Name of directory containing input files inside run dir",
)
@click.option("--output-dir", default=None, help="Custom output directory name inside run dir")
@click.option("--run-id", default=None, help="Custom run ID (defaults to timestamp)")
def run_agent(name, project_root, run_root, input_file, input_dir, output_dir, run_id):
    """Run an agent with the specified inputs.

    NAME is the name of the agent.
    """
    asyncio.run(_run_agent(name, project_root, run_root, input_file, input_dir, output_dir, run_id))


async def _run_agent(name, project_root, run_root, input_file, input_dir, output_dir, run_id):
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
        agent_name=name,
        run_root=run_root,
        input_dir=input_dir,
        output_dir=output_dir,
        run_id=run_id,
    )

    # TODO: Cleanup input section

    # Load input data
    input_data = {}
    if input_file:
        with open(input_file) as f:  # noqa: ASYNC230 :TODO_FUTURE
            input_data = json.load(f)

    # Prepare input files
    input_files = []
    if input_dir:
        input_dir_path = Path(input_dir)
        if input_dir_path.exists() and input_dir_path.is_dir():
            input_files = list(input_dir_path.glob("*"))

    # TODO: pass initial_inputs also via RunContext
    run_ctx.prepare_input(input_data, input_files)

    try:
        # Load agent
        agent_module = load_agent_module(project_root, f"agents/{name}/agent")
        if not agent_module:
            raise ValueError("Failed to get agent module")

        # Run agent in a subprocess for isolation
        async with IsolatedExecution(run_ctx) as executor:
            result = await executor.run(agent_module, input_data)

        # Process and save results
        run_ctx.save_output("final", result)
        run_ctx.complete_run()

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
