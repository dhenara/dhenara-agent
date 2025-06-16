import asyncio
import importlib
import logging
from pathlib import Path

import click

from dhenara.agent.run import IsolatedExecution
from dhenara.agent.runner import AgentRunner
from dhenara.agent.types import AgentRunConfig
from dhenara.agent.utils.shared import find_project_root

from ..utils.print_utils import print_error_summary, print_run_summary

logger = logging.getLogger(__name__)


@click.command(name="run")
@click.argument("identifier")
@click.option("--project-root", default=None, help="Root directory of the project repo")
@click.option("--previous-run-id", default=None, help="ID of a previous execution to inherit context from")
@click.option(
    "--entry-point",
    default=None,
    help=(
        "Specific point in the execution graph to begin from. "
        "Format can be a single element ID or a dot-notation path (e.g., 'agent_id.flow_id.node_id')"
    ),
)
def run_agent(
    identifier,
    project_root,
    previous_run_id,
    entry_point,
):
    """Run a DAD agent."""
    asyncio.run(
        _run_agent(
            identifier=identifier,
            project_root=project_root,
            previous_run_id=previous_run_id,
            start_hierarchy_path=entry_point,
        )
    )


async def _run_agent(
    identifier,
    project_root,
    previous_run_id,
    start_hierarchy_path,
):
    """Async implementation of run_agent."""

    # Find project root
    if not project_root:
        project_root = find_project_root()
    if not project_root:
        click.echo("Error: Not in a Dhenara project directory.")
        return

    # Load agent
    runner = load_runner_module(project_root, identifier)

    if not (runner and isinstance(runner, AgentRunner)):
        raise ValueError(f"Failed to get runner module inside project. runner={runner}")

    run_config = AgentRunConfig(
        previous_run_id=previous_run_id,
        start_hierarchy_path=start_hierarchy_path,
    )
    # Update run context with rerun parameters if provided
    runner.setup_run(run_config)

    try:
        # Run agent in a subprocess for isolation
        async with IsolatedExecution(runner.run_context) as executor:
            _result = await executor.run(
                runner=runner,
            )

        # Display rerun information if applicable
        run_type = "rerun" if run_config.previous_run_id else "standard run"
        start_info = ""
        if run_config.start_hierarchy_path:
            start_info += f"from {run_config.start_hierarchy_path}"

        print(f"Agent {run_type} completed successfully{start_info}. Run ID: {runner.run_context.run_id}")

        print_run_summary(runner.run_context)

        ## View the traces in the dashboard if the file exists
        # if run_ctx.trace_file.exists():
        #    # from dhenara.agent.observability.dashboards import view_trace_in_console
        #    # view_trace_in_console(file=run_ctx.trace_file)
        #    print("To launching dashboards , run")
        #    print(f"dhenara dashboard simple {run_ctx.trace_file} ")

        if runner.run_context.log_file.exists():
            print(f"Logs in {runner.run_context.log_file} ")

        print()

    except Exception as e:
        # Get the full error hierarchy as a string
        import traceback

        error_trace = traceback.format_exc()
        print(error_trace)

        error_msg = f"Error running agent {identifier}: {e}"
        logger.exception(error_msg)
        await runner.run_context.complete_run(status="failed", error_msg=error_msg)
        print_error_summary(str(e))


def load_runner_module(project_root: Path, identifier: str):
    """Load agent module from the specified path."""
    # agent_path = f"src/agents/{identifier}/agent"
    runner_path = f"src/runners/{identifier}"

    try:
        # Add current directory to path
        import sys

        sys.path.append(str(project_root))

        ## Agent
        # agent_module_path = agent_path.replace("/", ".")
        # agent_module = importlib.import_module(agent_module_path)

        # Runner
        # Convert file path notation to module notation
        runner_module_path = runner_path.replace("/", ".")
        # Import agent from path
        runner_module = importlib.import_module(runner_module_path)

        return runner_module.runner

    except ImportError as e:
        raise ValueError(f"Failed to import runner from project_root {project_root}  runner_path:{runner_path}: {e}")
    except AttributeError as e:
        raise ValueError(
            f"Failed to find runner definition in module project_root {project_root}  runner_path:{runner_path}: {e}"
        )
