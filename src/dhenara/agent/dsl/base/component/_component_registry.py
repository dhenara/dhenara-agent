import threading
from typing import Literal

from dhenara.agent.dsl.base import ComponentExecutor, ComponentTypeEnum


class ComponentExecutorRegistry:
    """Registry for component executors.

    Provides a central management system for registering and retrieving
    executors for different component types. Implemented as a singleton
    to ensure only one instance exists throughout the entire run.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._executors = {}
            return cls._instance

    def __init__(self):
        self._executors: dict[Literal["flow", "agent"], ComponentExecutor] = {}

    def register(
        self,
        component_type: ComponentTypeEnum,
        executor_class: type[ComponentExecutor],
    ) -> ComponentExecutor:
        """
        Register a executor class for a specific component type.

        Args:
            component_type: The type of component this executor can process
            executor_class: The executor class to register
        """

        with self._lock:
            if component_type.value not in self._executors:
                executor = executor_class()
                self._executors[component_type.value] = executor
            return self._executors[component_type.value]

    def get_executor(
        self,
        component_type: ComponentTypeEnum,
    ) -> ComponentExecutor | None:
        """
        Get the executor for a specific component type.

        Args:
            component_type: The type of component to get a executor for

        Returns:
            The executor instance or None if not registered
        """
        return self._executors.get(component_type.value)
