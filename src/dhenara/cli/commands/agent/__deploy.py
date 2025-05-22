import os
from pathlib import Path

import click
import yaml


def register(cli):
    cli.add_command(deploy)


@click.command("deploy")
@click.option("--env", default="dev", help="Environment to deploy to (dev, staging, prod)")
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to deployment config file")
def deploy(env, config):
    """Deploy a Dhenara agent or project."""
    # Get current directory
    current_dir = Path(os.getcwd())

    # Try to find config file
    if not config:
        default_config = current_dir / "config" / "deploy.yaml"
        if default_config.exists():
            config = default_config
        else:
            click.echo("Error: No deployment configuration found. Please provide a config file with --config.")
            return

    # Load config
    try:
        with open(config) as f:
            deploy_config = yaml.safe_load(f)
    except Exception as e:
        click.echo(f"Error loading config file: {e}")
        return

    # Check if environment is configured
    if env not in deploy_config:
        click.echo(f"Error: Environment '{env}' not found in config.")
        return

    env_config = deploy_config[env]

    # Detect agent/project type
    project_type = detect_project_type(current_dir)
    if not project_type:
        click.echo("Error: Unable to determine project type. Make sure you're in a valid Dhenara project directory.")
        return

    click.echo(f"Deploying {project_type} to {env} environment...")

    # Execute deployment based on project type
    if project_type == "agent":
        deploy_agent(current_dir, env_config)
    elif project_type == "app":
        deploy_app(current_dir, env_config)
    else:
        click.echo(f"Deployment for {project_type} not implemented yet.")


def detect_project_type(directory):
    """Detect the type of Dhenara project in the given directory."""
    # Check for agent markers
    if (directory / "src" / "agent.py").exists():
        return "agent"

    # Check for app markers
    if (directory / "app.py").exists() or (directory / "src" / "app.py").exists():
        return "app"

    # Default unknown
    return None


def deploy_agent(directory, config):
    """Deploy a Dhenara agent."""
    # Implementation depends on your deployment targets
    if config.get("platform") == "dhenara-cloud":
        click.echo("Deploying to Dhenara Cloud...")
        # Here you would implement the cloud deployment logic

    elif config.get("platform") == "docker":
        click.echo("Building Docker container...")
        # Build and push docker container

    elif config.get("platform") == "local":
        click.echo("Setting up local deployment...")
        # Setup local deployment

    click.echo("✅ Deployment completed!")


def deploy_app(directory, config):
    """Deploy a Dhenara application."""
    # Similar implementation to deploy_agent but for apps
    click.echo("App deployment not fully implemented yet.")
