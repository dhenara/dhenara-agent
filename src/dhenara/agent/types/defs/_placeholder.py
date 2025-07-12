class _Placeholder:
    """A singleton class representing a placeholder value."""

    _instance = None
    __slots__ = ()  # Prevent creation of instance __dict__

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "PLACEHOLDER"

    def __bool__(self):
        return False


# Create the single instance
PLACEHOLDER = _Placeholder()

# Set the type alias to be exactly the type of our instance
PlaceholderType = type(PLACEHOLDER)
