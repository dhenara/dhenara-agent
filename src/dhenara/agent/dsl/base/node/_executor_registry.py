import threading
from typing import Literal

from dhenara.agent.dsl.base import ExecutableTypeEnum, NodeExecutor


class NodeExecutorRegistry:
    """Registry for node executors.

    Provides a central management system for registering and retrieving
    executors for different node types.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._executors = {
                    "flow": {},
                    "agent": {},
                }
            return cls._instance

    def __init__(self):
        self._executors: dict[Literal["flow", "agent"], dict[str, type[NodeExecutor]]] = {
            val: {} for val in ExecutableTypeEnum.__members__.values()
        }

    def register(
        self,
        executable_type: ExecutableTypeEnum,
        node_type: str,
        executor_class: type[NodeExecutor],
    ) -> NodeExecutor:
        """
        Register a executor class for a specific node type.

        Args:
            node_type: The type of node this executor can process
            executor_class: The executor class to register
        """

        with self._lock:
            executor = executor_class()
            self._executors[executable_type.value][node_type] = executor
            return executor

    def get_executor(
        self,
        executable_type: ExecutableTypeEnum,
        node_type: str,
    ) -> NodeExecutor | None:
        """
        Get the executor class for a specific node type.

        Args:
            node_type: The type of node to get a executor for

        Returns:
            The executor class

        Raises:
            ValueError: If no executor is registered for the given node type
        """
        type_executors = self._executors.get(executable_type.value)
        if type_executors is None:
            print(self._executors)
            raise ValueError(
                f"No executor registered for executable type: {executable_type}. "
                f" Available types: {self._executors.keys()}"
            )
        executor_class = type_executors.get(node_type, None)
        return executor_class
