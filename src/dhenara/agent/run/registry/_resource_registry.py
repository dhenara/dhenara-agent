# dhenara/resources.py
import logging
import threading
from contextlib import contextmanager
from typing import Generic, TypeVar

from dhenara.agent.types.base import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ResourceRegistry(Generic[T]):
    """
    Registry for managing shared resources of a specific type.

    This class provides a thread-safe registry for storing and retrieving
    resources (like models, endpoints, flows) throughout the application.
    It supports both global resources and thread-local overrides.

    Type Parameters:
        T: The type of resource this registry manages (must be a BaseModel subclass)

    Example:
        # Create a registry for AIModel resources
        model_registry = ResourceRegistry[AIModel](AIModel)

        # Register a resource
        model_registry.register("gpt4", my_gpt4_model)

        # Retrieve a resource
        model = model_registry.get("gpt4")
    """

    def __init__(self, resource_type: type[T], name: str | None = None):
        """
        Initialize a new resource registry.

        Args:
            resource_type: The type of resource this registry will manage
            name: Optional name for this registry (for logging/debugging)
        """
        self.resource_type = resource_type
        self.name = name or resource_type.__name__
        self._resources: dict[str, T] = {}
        self._thread_local = threading.local()
        logger.debug(f"Initialized {self.name} registry")

    def register(self, name: str, resource: T) -> None:
        """
        Register a resource in the global registry.

        Args:
            name: Unique identifier for the resource
            resource: The resource instance to register

        Raises:
            TypeError: If the resource is not of the expected type
        """
        if not isinstance(resource, self.resource_type):
            raise TypeError(f"Resource must be of type {self.resource_type.__name__}")

        self._resources[name] = resource
        logger.debug(f"Registered resource '{name}' in {self.name} registry")

    def get(self, name: str) -> T | None:
        """
        Get a resource by name.

        Looks for the resource in the following order:
        1. Thread-local resources (if any thread-specific override exists)
        2. Global resources

        Args:
            name: The name of the resource to retrieve

        Returns:
            The requested resource or None if not found

        Example:
            model = model_registry.get("gpt4")
            if model:
                # Use the model
            else:
                # Handle missing resource
        """
        # Check thread-local override first
        thread_resources = getattr(self._thread_local, "resources", {})
        if name in thread_resources:
            return thread_resources[name]

        # Fall back to global resources
        return self._resources.get(name)

    def list_names(self) -> list[str]:
        """
        Get a list of all registered resource names.

        Returns:
            List of resource names
        """
        # Start with global resources
        all_names = set(self._resources.keys())

        # Add thread-local resources
        thread_resources = getattr(self._thread_local, "resources", {})
        all_names.update(thread_resources.keys())

        return sorted(all_names)

    def list_resources(self) -> dict[str, T]:
        """
        Get a dictionary of all registered resources.

        Returns:
            Dictionary mapping resource names to resource instances
        """
        # Start with global resources
        all_resources = dict(self._resources)

        # Override with thread-local resources
        thread_resources = getattr(self._thread_local, "resources", {})
        all_resources.update(thread_resources)

        return all_resources

    @contextmanager
    def override(self, name: str, resource: T):
        """
        Temporarily override a resource for the current thread.

        This creates a thread-local override that exists only for the
        duration of the context manager block.

        Args:
            name: The name of the resource to override
            resource: The replacement resource

        Example:
            # Temporarily use a different model
            with model_registry.override("gpt4", alternative_model):
                # This code will use the alternative model
                result = process_with_model()
            # Back to the original model
        """
        if not isinstance(resource, self.resource_type):
            raise TypeError(f"Resource must be of type {self.resource_type.__name__}")

        # Initialize thread-local resources if needed
        if not hasattr(self._thread_local, "resources"):
            self._thread_local.resources = {}

        # Store previous value
        previous = self._thread_local.resources.get(name)

        # Set override
        self._thread_local.resources[name] = resource
        logger.debug(f"Set thread-local override for resource '{name}' in {self.name} registry")

        try:
            yield
        finally:
            # Restore previous state
            if previous is not None:
                self._thread_local.resources[name] = previous
            else:
                del self._thread_local.resources[name]
            logger.debug(f"Removed thread-local override for resource '{name}' in {self.name} registry")
