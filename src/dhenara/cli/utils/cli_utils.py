from pathlib import Path


def is_project_dir(path):
    """Check if the path is a Dhenara project directory."""
    return (Path(path) / ".dhenara").exists()


def find_project_root() -> Path:
    """Find the project root by looking for .dhenara directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".dhenara").exists():
            return current
        current = current.parent
    return None
