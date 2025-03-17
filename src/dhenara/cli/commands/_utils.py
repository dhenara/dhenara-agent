import re
import unicodedata


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
