import logging
import uuid
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)
# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from dhenara.agent.dsl.base import ExecutionContext
else:
    ExecutionContext = Any


class ExecutionContextRegistry:
    """
    Central registry for managing execution contexts with enhanced hierarchical navigation
    and optional memory optimization.
    """

    def __init__(self, enable_caching: bool = True):
        """
        Initialize the execution context registry.

        Args:
            enable_caching: If True, contexts are cached in memory for faster lookup.
                           If False, only path relationships are stored to optimize memory usage.
        """
        self.enable_caching = enable_caching
        # Only populated when caching is enabled
        self.contexts_by_path: dict[str, ExecutionContext] = {}
        # Always maintained regardless of caching
        self.context_id_to_path: dict[uuid.UUID, str] = {}
        self.path_to_context_id: dict[str, uuid.UUID] = {}

        # Hierarchy relationship maps - always maintained
        self.parent_map: dict[str, str] = {}  # path -> parent_path
        self.children_map: dict[str, list[str]] = {}  # path -> [child_paths]

    def register(self, context: ExecutionContext) -> None:
        """Register a context in the registry."""
        path = context.get_hierarchy_path(path_joiner=".")
        context_id = context.context_id

        # Store mappings regardless of caching
        self.path_to_context_id[path] = context_id
        self.context_id_to_path[context_id] = path

        # Store the actual context if caching is enabled
        if self.enable_caching:
            self.contexts_by_path[path] = context

        # Maintain hierarchy relationship maps
        if context.parent:
            parent_path = ".".join(context.parent.find_parent_component_ids())
            self.parent_map[path] = parent_path

            if parent_path not in self.children_map:
                self.children_map[parent_path] = []

            self.children_map[parent_path].append(path)

        logger.debug(f"Registered context: {path}")

    def get_context_by_path(self, path: str) -> ExecutionContext | None:
        """Get a context by its exact hierarchical path."""
        if not self.enable_caching:
            logger.warning("Context caching is disabled, cannot retrieve contexts directly")
            return None

        return self.contexts_by_path.get(path)

    def lookup_context_by_partial_path(
        self,
        partial_path: str,
        current_context_path: str | None = None,
        fetch_context: bool = True,
    ) -> tuple[str | None, ExecutionContext | None]:
        """
        Find a context or path by a partial path, with flexible return options.

        This enhanced method allows you to retrieve the context object, the full path,
        or both, based on the return_type parameter.

        This method tries to find a context in the following order:
        1. Direct match with the partial path
        2. Relative to the current context
        3. As a sibling of the current context
        4. By moving up the hierarchy and searching
        5. By checking if any path ends with the partial path
        6. By checking if the partial path matches a continuous segment of any path

        Args:
            partial_path: The partial path to search for (e.g., "planner" or "planner.plan_generator")
            current_context_path: The current context path to use as a reference point (optional)
            fetch_context: Whether to return the matching context or not

        Returns:
             context and path
        """
        if not self.enable_caching and fetch_context:
            logger.warning("Context caching is disabled, cannot retrieve contexts directly")

        fetch_matching_context = self.enable_caching and fetch_context

        # logger.debug(f"Searching for context: partial_path={partial_path}, current_path={current_context_path}")

        # Track the matching path when found
        matching_path = None
        matching_context = None

        # 1. Direct match - check if the partial path exists directly
        if partial_path in self.contexts_by_path:
            matching_path = partial_path
            if fetch_matching_context:
                matching_context = self.contexts_by_path[partial_path]

        # Only proceed with relative path resolution if we have a current context
        elif current_context_path:
            # 2. Check if it's a direct child of the current context
            child_path = f"{current_context_path}.{partial_path}"
            if child_path in self.contexts_by_path:
                matching_path = child_path
                if fetch_matching_context:
                    matching_context = self.contexts_by_path[child_path]

            # 3. Check if it's a sibling (has the same parent)
            elif not matching_path:
                parent_path = self.parent_map.get(current_context_path)
                if parent_path:
                    sibling_path = f"{parent_path}.{partial_path}"
                    if sibling_path in self.contexts_by_path:
                        matching_path = sibling_path
                        if fetch_matching_context:
                            matching_context = self.contexts_by_path[sibling_path]

            # 4. Navigate up the hierarchy
            if not matching_path:
                ancestor_path = current_context_path
                while ancestor_path:
                    # Move up one level
                    ancestor_path = self.parent_map.get(ancestor_path)
                    if not ancestor_path:
                        break

                    # Try this level + partial path
                    test_path = f"{ancestor_path}.{partial_path}"
                    if test_path in self.contexts_by_path:
                        matching_path = test_path
                        if fetch_matching_context:
                            matching_context = self.contexts_by_path[test_path]
                        break

        # 5. Look for any path that ends with the partial path
        if not matching_path:
            suffix = f".{partial_path}"
            for path, ctx in self.contexts_by_path.items():
                if path.endswith(suffix) or path == partial_path:
                    matching_path = path
                    if fetch_matching_context:
                        matching_context = ctx
                    break

        # 6. Look for continuous segment matching - finds segments that appear as-is in the path
        if not matching_path:
            partial_parts = partial_path.split(".")
            for path, ctx in self.contexts_by_path.items():
                path_parts = path.split(".")

                # Check if partial_parts appears as a continuous segment in path_parts
                for i in range(len(path_parts) - len(partial_parts) + 1):
                    if path_parts[i : i + len(partial_parts)] == partial_parts:
                        matching_path = path
                        if fetch_matching_context:
                            matching_context = ctx
                        break
                if matching_path:
                    break

        # Return based on the requested return type
        if matching_path or matching_context:
            logger.debug(
                f"Found match: path={matching_path}, "
                f" context={matching_context.component_id if matching_context else None}"
            )

        return (matching_path, matching_context)

    def get_children(self, context: ExecutionContext) -> list[ExecutionContext]:
        """Get all children of a context."""
        if not self.enable_caching:
            logger.warning("Context caching is disabled, cannot retrieve child contexts directly")
            return []

        path = context.get_hierarchy_path(path_joiner=".")
        children_paths = self.get_children_paths(path)
        return [
            self.contexts_by_path[child_path] for child_path in children_paths if child_path in self.contexts_by_path
        ]

    def get_parent(self, context: ExecutionContext) -> ExecutionContext | None:
        """Get the parent context of a given context."""
        if not self.enable_caching:
            # If caching is disabled, just use the parent reference directly
            return context.parent

        path = context.get_hierarchy_path(path_joiner=".")
        parent_path = self.get_parent_path(path)
        if parent_path:
            return self.contexts_by_path.get(parent_path)
        return None

    def get_parent_path(self, path: str) -> str | None:
        """Get the parent path of a given context path."""
        return self.parent_map.get(path)

    def get_children_paths(self, path: str) -> list[str]:
        """Get all children paths of a given context path."""
        return self.children_map.get(path, [])

    def find_contexts_by_pattern(self, pattern: str) -> list[ExecutionContext]:
        """
        Find all contexts that match a given pattern (using simple string contains).

        Args:
            pattern: A pattern to match against context paths

        Returns:
            List of matching contexts
        """
        if not self.enable_caching:
            logger.warning("Context caching is disabled, cannot retrieve contexts directly")
            return []

        return [ctx for path, ctx in self.contexts_by_path.items() if pattern in path]

    def set_caching_enabled(self, enable: bool):
        """Enable or disable context caching."""
        if self.enable_caching == enable:
            return

        self.enable_caching = enable
        if not enable:
            # Clear contexts but keep relationship maps when disabling caching
            self.contexts_by_path.clear()
            logger.info("Execution context caching disabled, cleared cached contexts")
        else:
            logger.info("Execution context caching enabled")

    def clear(self):
        """Clear all stored contexts and mappings."""
        self.contexts_by_path.clear()
        self.context_id_to_path.clear()
        self.path_to_context_id.clear()
        self.parent_map.clear()
        self.children_map.clear()
        logger.info("Execution context registry cleared")
