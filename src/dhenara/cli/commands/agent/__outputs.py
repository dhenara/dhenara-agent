# dhenara/cli/commands/outputs.py
import logging

import click

from dhenara.agent.utils.git import RunOutcomeRepository
from dhenara.agent.utils.shared import find_project_root

logger = logging.getLogger(__name__)


def register(cli):
    cli.add_command(outputs)


@click.group("outputs")
def outputs():
    """Manage agent execution outputs."""
    pass


@outputs.command("list")
@click.option("--run-id", help="Filter by run ID")
def list_outputs(run_id):
    """List outputs from agent executions."""
    project_root = find_project_root()
    if not project_root:
        click.echo("Error: Not in a Dhenara project directory.")
        return

    output_repo = RunOutcomeRepository(project_root / "runs" / "output")

    if run_id:
        history = output_repo.get_run_history(run_id)
        if not history:
            click.echo(f"No outputs found for run ID {run_id}")
            return

        click.echo(f"Execution History for {run_id}:")
        for i, entry in enumerate(history):
            click.echo(f"{i + 1}. [{entry['date']}] {entry['message']} ({entry['commit']})")
    else:
        # List all runs
        runs = output_repo.list_runs()
        if not runs:
            click.echo("No runs found.")
            return

        click.echo("Available Runs:")
        for i, run_id in enumerate(runs):
            click.echo(f"{i + 1}. {run_id}")


@outputs.command("compare")
@click.argument("run1")
@click.argument("run2")
@click.option("--node", help="Compare specific node outputs")
def compare_outputs(run1, run2, node):
    """Compare outputs between two runs."""
    project_root = find_project_root()
    if not project_root:
        click.echo("Error: Not in a Dhenara project directory.")
        return

    output_repo = RunOutcomeRepository(project_root / "runs" / "output")
    changes = output_repo.compare_runs(run1, run2, node)

    click.echo(f"Comparing {run1} and {run2}:")
    if not changes:
        click.echo("No differences found.")
        return

    for change in changes:
        status_marker = "+" if change["status"] == "A" else "-" if change["status"] == "D" else "M"
        click.echo(f"{status_marker} {change['path']}")


@outputs.command("checkout")
@click.argument("run-id")
def checkout_run(run_id):
    """Check out a specific run branch to examine its outputs."""
    project_root = find_project_root()
    if not project_root:
        click.echo("Error: Not in a Dhenara project directory.")
        return

    _output_repo = RunOutcomeRepository(project_root / "runs" / "output")

    import subprocess

    try:
        subprocess.run(
            ["git", "checkout", f"run/{run_id}"],
            cwd=project_root / "runs" / "output",
            check=True,
        )
        click.echo(f"Checked out run {run_id}")
    except subprocess.CalledProcessError:
        click.echo(f"Error: Unable to checkout run {run_id}")
