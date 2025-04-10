import subprocess
import time
import webbrowser
from pathlib import Path

import click


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


def start_jaeger_dashboard():
    """Start the Jaeger dashboard using Docker Compose."""
    compose_file = find_docker_compose_file()

    click.echo("Starting Jaeger dashboard...")
    subprocess.run(["docker-compose", "-f", str(compose_file), "up", "-d"], check=True)

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
        subprocess.run(["docker-compose", "-f", str(compose_file), "down"], check=True)


def is_jaeger_running():
    """Check if Jaeger is already running."""
    try:
        import requests

        response = requests.get("http://localhost:16686", timeout=1)
        return response.status_code == 200
    except:
        return False


def run_dashboard():
    """Run the Jaeger dashboard."""
    if is_jaeger_running():
        click.echo("Jaeger is already running. Opening browser...")
        webbrowser.open("http://localhost:16686")
    else:
        start_jaeger_dashboard()


if __name__ == "__main__":
    run_dashboard()
