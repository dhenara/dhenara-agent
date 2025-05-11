import click

from dhenara.agent.observability.dashboards import run_dashboard, run_jaeger_dashboard, run_zipkin_dashboard


def register(cli):
    pass
    # cli.add_command(dashboard) # TODO_FUTURE


@click.group("dashboard")
def dashboard():
    """Run various visualization dashboards."""
    pass


@dashboard.command("simple")
@click.argument("file", type=click.Path(exists=True))
@click.option("--port", type=int, default=8080, help="Port for the dashboard server")
def simple_dashboard(file, port):
    """Run the simple built-in dashboard."""
    run_dashboard(file, port)


@dashboard.command("jaeger")
def jaeger_dashboard():
    """Run the Jaeger dashboard (requires Docker)."""
    run_jaeger_dashboard()


@dashboard.command("zipkin")
def zipkin_dashboard():
    """Run the Zipkin dashboard (requires Docker)."""
    run_zipkin_dashboard()
