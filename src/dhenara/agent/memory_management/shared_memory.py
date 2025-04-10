# src/dhenara/agent/memory_management/shared_memory.py
from typing import Any


## TODO: Unused
class SharedMemory:
    """
    Simple shared memory system for communication between agents.
    Uses namespaces to avoid key collisions.
    """

    def __init__(self):
        self._memory: dict[str, dict[str, Any]] = {}

    def set(self, namespace: str, key: str, value: Any) -> None:
        """Set a value in the specified namespace."""
        if namespace not in self._memory:
            self._memory[namespace] = {}
        self._memory[namespace][key] = value

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """Get a value from the specified namespace."""
        if namespace not in self._memory:
            return default
        return self._memory[namespace].get(key, default)

    def delete(self, namespace: str, key: str) -> None:
        """Delete a key from the specified namespace."""
        if namespace in self._memory and key in self._memory[namespace]:
            del self._memory[namespace][key]

    def list_namespaces(self) -> list[str]:
        """List all namespaces."""
        return list(self._memory.keys())

    def list_keys(self, namespace: str) -> list[str]:
        """List all keys in a namespace."""
        if namespace not in self._memory:
            return []
        return list(self._memory[namespace].keys())
