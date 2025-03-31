import subprocess
import time
import webbrowser

import click

'''
def find_docker_compose_file():
    """Find the jaeger-docker-compose.yaml file."""
    # Try current directory first
    if Path("jaeger-docker-compose.yaml").exists():
        return Path("jaeger-docker-compose.yaml")

    # Try package directory
    package_dir = Path(__file__).parent
    if (package_dir / "jaeger-docker-compose.yaml").exists():
        return package_dir / "jaeger-docker-compose.yaml"

    # Use the one from the package as fallback
    return Path(__file__).parent / "jaeger-docker-compose.yaml"
'''


def start_jaeger_dashboard():
    """Start the Jaeger dashboard using Docker."""
    click.echo("Starting Jaeger dashboard...")

    # Run Jaeger container with all required ports
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            "dhenara-jaeger",
            "-p",
            "16686:16686",  # Jaeger UI
            "-p",
            "14268:14268",  # Collector HTTP endpoint
            "-p",
            "6831:6831/udp",  # Jaeger thrift compact
            "-e",
            "COLLECTOR_ZIPKIN_HOST_PORT=:9411",
            "jaegertracing/all-in-one:latest",
        ],
        check=True,
    )

    # Wait for Jaeger to start
    click.echo("Waiting for Jaeger to start...")
    time.sleep(5)

    # Open browser to Jaeger UI
    webbrowser.open("http://localhost:16686")
    click.echo("Jaeger dashboard started at: http://localhost:16686")
    click.echo("Press Ctrl+C to stop")

    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("Stopping Jaeger dashboard...")
        subprocess.run(["docker", "stop", "dhenara-jaeger"], check=True)
        subprocess.run(["docker", "rm", "dhenara-jaeger"], check=True)


def is_jaeger_running():
    """Check if Jaeger is already running."""
    try:
        # Check if the container is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=dhenara-jaeger", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        if "dhenara-jaeger" in result.stdout:
            return True

        # Also check if the port is accessible (in case running elsewhere)
        import requests

        response = requests.get("http://localhost:16686", timeout=1)
        return response.status_code == 200
    except:
        return False


# def run_dashboard():
#    """Run the Jaeger dashboard."""
#    if is_jaeger_running():
#        click.echo("Jaeger is already running. Opening browser...")
#        webbrowser.open("http://localhost:16686")
#    else:
#        start_jaeger_dashboard()


def ensure_jaeger_container():
    """Check if Jaeger container exists but is stopped, and restart it if needed."""
    try:
        # Check if container exists but is not running
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=dhenara-jaeger", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
        )

        if "dhenara-jaeger" in result.stdout:
            # Container exists, check if it's running
            running = subprocess.run(
                ["docker", "ps", "--filter", "name=dhenara-jaeger", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True,
            )

            if "dhenara-jaeger" not in running.stdout:
                # Container exists but is not running, start it
                click.echo("Restarting existing Jaeger container...")
                subprocess.run(["docker", "start", "dhenara-jaeger"], check=True)
                return True
            return True
        return False
    except:
        return False


def check_docker_installed():
    """Check if Docker is installed and accessible."""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def run_dashboard():
    """Run the Jaeger dashboard."""
    if not check_docker_installed():
        click.echo("Error: Docker is not installed or not in PATH.")
        click.echo("\nPlease install Docker on your system:")
        click.echo(" - Windows/Mac: https://www.docker.com/products/docker-desktop")
        click.echo(" - Linux: https://docs.docker.com/engine/install/")
        click.echo("\nAfter installation, make sure the Docker daemon is running.")
        return

    if is_jaeger_running():
        click.echo("Jaeger is already running. Opening browser...")
        webbrowser.open("http://localhost:16686")
    elif ensure_jaeger_container():
        # Container existed and was restarted
        click.echo("Jaeger container restarted. Opening browser...")
        time.sleep(2)  # Give it a moment to start
        webbrowser.open("http://localhost:16686")
    else:
        # Need to create a new container
        start_jaeger_dashboard()


def stop_jaeger():
    """Stop the Jaeger dashboard."""
    if not check_docker_installed():
        click.echo("Error: Docker is not installed or not in PATH.")
        return

    try:
        # Check if container exists
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=dhenara-jaeger", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
        )

        if "dhenara-jaeger" in result.stdout:
            click.echo("Stopping Jaeger container...")
            subprocess.run(["docker", "stop", "dhenara-jaeger"], check=True)
            click.echo("Jaeger container stopped.")
        else:
            click.echo("No Jaeger container found.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error stopping Jaeger container: {e}")


if __name__ == "__main__":
    run_dashboard()

# @dashboard.command("stop-jaeger")
# def stop_jaeger_command():
#    """Stop the Jaeger dashboard."""
#    from dhenara.agent.observability.dashboards.jaeger import stop_jaeger
#
#    stop_jaeger()
