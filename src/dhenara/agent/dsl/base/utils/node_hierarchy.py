# dhenara/agent/utils/node_hierarchy.py
import logging
from pathlib import Path
from typing import Any

from dhenara.agent.dsl.base import NodeID

logger = logging.getLogger(__name__)


class NodeHierarchyHelper:
    """Utility class to determine and manage node hierarchies in flows."""

    @staticmethod
    def get_node_hierarchy_path(
        execution_context,  # : ExecutionContext,
        node_id: NodeID,
    ) -> str:
        """
        Determine the hierarchical path of a node within a component definition.

        Args:
            execution_context: The current execution context
            node_id: The ID of the node

        Returns:
            A path string representing the node's hierarchy (e.g., "main_flow/subflow1/node1")
        """
        # Skip if no component definition
        if not execution_context.component_definition:
            return node_id

        component_path_parts = NodeHierarchyHelper._find_parent_component_ids(execution_context)

        # Add current node id
        path_parts = [node_id]

        try:
            # Get component definition
            component_def = execution_context.component_definition

            # Get the current node's element
            current_element = component_def.get_element_by_id(node_id)
            if not current_element:
                return node_id

            # Check if this node is part of a subflow or nested component
            parent_element_id = NodeHierarchyHelper._find_parent_element_id(component_def, node_id)

            # If we found a parent, add it to the path
            if parent_element_id:
                path_parts.insert(0, parent_element_id)

                # Continue looking for higher-level parents
                parent_of_parent = NodeHierarchyHelper._find_parent_element_id(component_def, parent_element_id)
                while parent_of_parent:
                    path_parts.insert(0, parent_of_parent)
                    parent_of_parent = NodeHierarchyHelper._find_parent_element_id(component_def, parent_of_parent)

            final_path_parts = [*component_path_parts, *path_parts]
            # Join path parts with forward slashes
            return "/".join(final_path_parts)

        except Exception as e:
            # Log error but don't fail - fall back to just the node ID
            logger.error(f"Error determining node hierarchy for {node_id}: {e}")
            return node_id

    @staticmethod
    def get_component_hierarchy_path(
        execution_context,  # : ExecutionContext,
        component_id: NodeID,
    ) -> str:
        # Skip if no component definition
        # if not execution_context.component_definition:
        #    return component_id

        component_path_parts = NodeHierarchyHelper._find_parent_component_ids(execution_context)

        # Add current node id
        path_parts = [component_id]

        try:
            # Get component definition
            component_def = execution_context.component_definition

            # Get the current node's element
            current_element = component_def.get_element_by_id(component_id)
            if not current_element:
                return component_id

            # Check if this node is part of a subflow or nested component
            parent_element_id = NodeHierarchyHelper._find_parent_element_id(component_def, component_id)

            # If we found a parent, add it to the path
            if parent_element_id:
                path_parts.insert(0, parent_element_id)

                # Continue looking for higher-level parents
                parent_of_parent = NodeHierarchyHelper._find_parent_element_id(component_def, parent_element_id)
                while parent_of_parent:
                    path_parts.insert(0, parent_of_parent)
                    parent_of_parent = NodeHierarchyHelper._find_parent_element_id(component_def, parent_of_parent)

            final_path_parts = [*component_path_parts, *path_parts]
            # Join path parts with forward slashes
            return "/".join(final_path_parts)

        except Exception as e:
            # Log error but don't fail - fall back to just the node ID
            logger.error(f"Error determining node hierarchy for {component_id}: {e}")
            return component_id

    @staticmethod
    def _find_parent_component_ids(execution_context) -> list[str]:
        comp_path_parts = [execution_context.component_id]

        parent_ctx = execution_context.parent
        while parent_ctx is not None:
            comp_path_parts.append(parent_ctx.component_id)
            parent_ctx = parent_ctx.parent

        comp_path_parts.reverse()  # Reverse the order
        return comp_path_parts

    @staticmethod
    def _find_parent_element_id(component_def: Any, node_id: str) -> str | None:
        """
        Find the ID of the parent component containing the specified node.

        Args:
            component_def: The component definition
            node_id: The ID of the node to find the parent for

        Returns:
            The ID of the parent component, or None if not found
        """
        # This implementation depends on how nested components are represented
        # in your component definition. Here's a simplified version:

        # Check if there are containers/blocks that might have children
        for element in component_def.elements:
            # Check for flow blocks, conditionals, loops, etc.
            if hasattr(element, "elements") and element.elements:
                # Check if any of the child elements match our node_id
                for child in element.elements:
                    if hasattr(child, "id") and child.id == node_id:
                        # Found a match - return the parent ID if it has one
                        return getattr(element, "id", None)

            # Check for conditional branches
            if hasattr(element, "then_branch") and element.then_branch:
                for child in element.then_branch.elements:
                    if hasattr(child, "id") and child.id == node_id:
                        return getattr(element, "id", None)

            if hasattr(element, "else_branch") and element.else_branch:
                for child in element.else_branch.elements:
                    if hasattr(child, "id") and child.id == node_id:
                        return getattr(element, "id", None)

        return None

    @staticmethod
    def create_storage_path(base_dir: Path, hierarchy_path: str) -> Path:
        """
        Create a filesystem path from a hierarchy path.

        Args:
            base_dir: The base directory
            hierarchy_path: The hierarchy path (e.g., "main_flow/subflow1/node1")

        Returns:
            A Path object for the full storage path
        """
        path = base_dir / hierarchy_path
        path.mkdir(parents=True, exist_ok=True)
        return path
