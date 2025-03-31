import subprocess
import time
import webbrowser
from pathlib import Path

import click


def find_docker_compose_file():
    """Find the zipkin-docker-compose.yaml file."""
    # Try current directory first
    if Path("zipkin-docker-compose.yaml").exists():
        return Path("zipkin-docker-compose.yaml")

    # Try package directory
    package_dir = Path(__file__).parent
    if (package_dir / "zipkin-docker-compose.yaml").exists():
        return package_dir / "zipkin-docker-compose.yaml"

    # Use the one from the package as fallback
    return Path(__file__).parent / "zipkin-docker-compose.yaml"


def start_zipkin_dashboard():
    """Start the Zipkin dashboard using Docker Compose."""
    compose_file = find_docker_compose_file()

    click.echo("Starting Zipkin dashboard...")
    subprocess.run(["docker-compose", "-f", str(compose_file), "up", "-d"], check=True)

    # Wait for Zipkin to start
    click.echo("Waiting for Zipkin to start...")
    time.sleep(5)

    # Open browser to Zipkin UI
    webbrowser.open("http://localhost:9411")
    click.echo("Zipkin dashboard started at: http://localhost:9411")
    click.echo("Press Ctrl+C to stop")

    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("Stopping Zipkin dashboard...")
        subprocess.run(["docker-compose", "-f", str(compose_file), "down"], check=True)


def is_zipkin_running():
    """Check if Zipkin is already running."""
    try:
        import requests

        response = requests.get("http://localhost:9411/api/v2/services", timeout=1)
        return response.status_code == 200
    except:
        return False


def run_dashboard():
    """Run the Zipkin dashboard."""
    if is_zipkin_running():
        click.echo("Zipkin is already running. Opening browser...")
        webbrowser.open("http://localhost:9411")
    else:
        start_zipkin_dashboard()


if __name__ == "__main__":
    run_dashboard()
