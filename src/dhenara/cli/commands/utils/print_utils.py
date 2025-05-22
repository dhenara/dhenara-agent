import click


def print_styled_header(text, color=None):
    """Print a styled header with optional color."""
    colors = {
        "green": "\033[92m",
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "purple": "\033[95m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "underline": "\033[4m",
        "reset": "\033[0m",
    }

    styled_text = f"{colors.get(color, '')}{colors['bold']}{text}{colors['reset']}"
    click.echo(styled_text)


def print_info(label, value, indent=2):
    """Print a label-value pair with proper formatting."""
    colors = {
        "label": "\033[96m",  # Cyan for labels
        "value": "\033[97m",  # White for values
        "reset": "\033[0m",
    }
    spaces = " " * indent
    click.echo(f"{spaces}{colors['label']}{label}:{colors['reset']} {colors['value']}{value}{colors['reset']}")


def print_command(command, indent=6):
    """Print a command with proper formatting."""
    colors = {
        "command": "\033[93m",  # Yellow for commands
        "reset": "\033[0m",
    }
    spaces = " " * indent
    click.echo(f"{spaces}{colors['command']}$ {command}{colors['reset']}")


def print_run_summary(run_ctx):
    """Print a beautifully formatted run summary."""
    # Clear some space
    click.echo("\n")

    # Print header with status
    print_styled_header("✅ RUN COMPLETED SUCCESSFULLY", "green")

    # Print horizontal separator
    click.echo("─" * 80)

    # Print run details
    print_info("Run ID", run_ctx.run_id)
    print_info("Artifacts location", f"{run_ctx.run_dir}")
    # print_info("Outcome repository", run_ctx.outcome_repo_dir)

    # TODO_FUTURE:Enable outcome commits and show user messages
    #
    # Print next steps section
    # click.echo("\n")
    # print_styled_header("NEXT STEPS:", "blue")
    # print_info("To view the outcome, checkout the working branch:", "", indent=2)
    # print_command(f"cd {run_ctx.outcome_repo_dir}")
    # print_command(f"git checkout {run_ctx.git_branch_name}")

    # Add some space at the end
    click.echo("\n")


def print_error_summary(error_message):
    """Print a beautifully formatted error summary."""
    # Clear some space
    click.echo("\n")

    # Print header with status
    print_styled_header("❌ RUN FAILED", "red")

    # Print horizontal separator
    click.echo("─" * 80)

    # Print error details
    print_info("Error", error_message)

    # Add some space at the end
    click.echo("\n")
