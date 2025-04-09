import asyncio
import importlib
import logging
from pathlib import Path

import click

from dhenara.agent.run import AgentRunner, IsolatedExecution
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
@click.option(
    "--previous-run-id",
    default=None,
    help="ID of a previous run to use as a base for this run",
)
@click.option(
    "--agent-start-node-id",
    default=None,
    help="Node ID to start execution from (skips all previous nodes)",
)
@click.option(
    "--flow-start-node-id",
    default=None,
    help="Node ID to start execution from (skips all previous nodes)",
)
def run_agent(
    identifier,
    project_root,
    previous_run_id,
    agent_start_node_id,
    flow_start_node_id,
):
    """Run an agent with the specified inputs.

    NAME is the name of the agent.

    Examples:
        dhenara run agent my_agent                     # Run the agent normally
        dhenara run agent my_agent --previous-run-id run_123  # Rerun a previous execution
        dhenara run agent my_agent --start-node-id node2     # Start execution from node2
        dhenara run agent my_agent --previous-run-id run_123 --start-node-id node2  # Rerun from node2
    """
    asyncio.run(
        _run_agent(
            identifier,
            project_root,
            previous_run_id,
            agent_start_node_id,
            flow_start_node_id,
        )
    )


async def _run_agent(
    identifier,
    project_root,
    previous_run_id,
    agent_start_node_id,
    flow_start_node_id,
):
    """Async implementation of run_agent."""
    # Find project root
    if not project_root:
        project_root = find_project_root()
    if not project_root:
        click.echo("Error: Not in a Dhenara project directory.")
        return

    # Load agent
    runner = load_runner_module(project_root, f"runner/{identifier}")
    if not (runner and isinstance(runner, AgentRunner)):
        raise ValueError(f"Failed to get runner module inside project. runner={runner}")

    # Update run context with rerun parameters if provided
    runner.set_previous_run_in_run_ctx(
        previous_run_id=previous_run_id,
        agent_start_node_id=agent_start_node_id,
        flow_start_node_id=flow_start_node_id,
    )

    try:
        # Run agent in a subprocess for isolation
        async with IsolatedExecution(runner.run_context) as executor:
            _result = await executor.run(
                runner=runner,
            )

        # Display rerun information if applicable
        run_type = "rerun" if previous_run_id else "standard run"
        start_info = (
            f"from node {agent_start_node_id or ''}:{flow_start_node_id or ''}"
            if agent_start_node_id or flow_start_node_id
            else "from beginning"
        )
        print(f"Agent {run_type} completed successfully {start_info}. Run ID: {runner.run_context.run_id}")

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
        logger.exception(f"Error running agent {identifier}: {e}")
        runner.run_context.metadata["error"] = str(e)
        runner.run_context.complete_run(status="failed")
        print_error_summary(str(e))


def load_runner_module(project_root: Path, agent_dir_path: str):
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
        return run_module.runner

    except ImportError as e:
        logger.error(f"Failed to import agent from project_root {project_root} path {agent_dir_path}: {e}")
    except AttributeError as e:
        logger.error(
            f"Failed to find agent definition in module project_root {project_root} path {agent_dir_path}: {e}"
        )
