import os
import re
import unicodedata
from pathlib import Path

import yaml


def validate_name(name):
    """
    Validate that a name contains only allowed characters.

    Args:
        name (str): The name to validate

    Returns:
        bool: True if the name is valid, False otherwise
    """
    if not name or len(name.strip()) == 0:
        return False

    # Allow alphanumeric characters, spaces, hyphens, and underscores
    pattern = r"^[a-zA-Z0-9\s\-_]+$"
    return bool(re.match(pattern, name))


def generate_identifier(name, use_hyphens=False):
    """
    Generate a standardized identifier from a name.

    Args:
        name (str): The name to convert to an identifier
        use_hyphens (bool): If True, use hyphens instead of underscores for word separation
                           (suitable for project names, package names, etc.)

    Returns:
        str: A valid identifier derived from the name
    """
    if not name:
        return ""

    # Convert to lowercase
    identifier = name.lower()

    # Normalize unicode characters (handle accented characters)
    identifier = unicodedata.normalize("NFKD", identifier)
    identifier = "".join([c for c in identifier if not unicodedata.combining(c)])

    # Replace spaces with underscores or hyphens
    separator = "-" if use_hyphens else "_"
    identifier = re.sub(r"[\s\-_]+", separator, identifier)

    # Remove any non-alphanumeric characters (except separators)
    pattern = f"[^a-z0-9{separator}]"
    identifier = re.sub(pattern, "", identifier)

    # Ensure it starts with a letter (for Python identifiers)
    if not use_hyphens and identifier and not identifier[0].isalpha():
        identifier = f"x{identifier}"

    # Ensure it's not empty
    if not identifier:
        identifier = "unnamed_project" if use_hyphens else "unnamed_item"

    return identifier


def get_project_config(project_dir=None):
    """
    Read the project configuration from the .dhenara/config.yaml file.

    Args:
        project_dir (str or Path, optional): The project directory path.
                                            If None, uses the current working directory.

    Returns:
        dict: The project configuration, or None if not found or invalid
    """
    project_dir = Path(project_dir or os.getcwd())
    config_path = project_dir / ".dhenara" / "config.yaml"

    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        return config
    except (OSError, yaml.YAMLError):
        return None


def get_project_identifier(project_dir=None):
    """
    Get the project identifier from the project configuration.

    Args:
        project_dir (str or Path, optional): The project directory path.
                                            If None, uses the current working directory.

    Returns:
        str: The project identifier, or None if not found
    """
    config = get_project_config(project_dir)

    # Handle both the new nested format and legacy flat format
    if config:
        if "project" in config and "identifier" in config["project"]:
            return config["project"]["identifier"]
        elif "name" in config:
            # Legacy format - derive identifier from name
            return generate_identifier(config["name"], use_hyphens=True)

    return None


def is_project_dir(directory=None):
    """
    Check if the specified directory is a Dhenara project.

    Args:
        directory (str or Path, optional): Directory to check.
                                          If None, uses the current working directory.

    Returns:
        bool: True if the directory is a Dhenara project, False otherwise
    """
    directory = Path(directory or os.getcwd())
    config_file = directory / ".dhenara" / "config.yaml"
    # return (Path(path) / ".dhenara").exists()
    return config_file.exists()


def find_project_root() -> Path:
    """Find the project root by looking for .dhenara directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".dhenara").exists():
            return current
        current = current.parent
    return None
