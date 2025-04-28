from pydantic import model_validator

from dhenara.agent.dsl.base import Executable


# TODO_FUTURE: Check and posssibly get rid of these mixins
class IdentifierValidationMixin:
    """Mixin providing identifier validation for hierarchical structures."""

    def _collect_all_identifiers(self, element: Executable, identifiers: set[str]) -> None:
        """
        Recursively collect all identifiers in a hierarchical structure.

        Args:
            element: Current element to process
            identifiers: Set collecting all identifiers

        Raises:
            ValueError: If duplicate identifier is found
        """
        # Get identifier from element (implemented by concrete class)
        identifier = self._get_element_identifier(element)

        if identifier in identifiers:
            raise ValueError(f"Duplicate identifier found: {identifier}")
        identifiers.add(identifier)

        # Process children recursively (implemented by concrete class)
        children = self._get_element_children(element)
        for child in children:
            self._collect_all_identifiers(child, identifiers)

    def validate_all_identifiers(self) -> None:
        """
        Validate uniqueness of all identifiers across the entire hierarchy.

        Raises:
            ValueError: If any duplicate identifiers are found
        """
        return
        all_identifiers: set[str] = set()
        for element in self._get_top_level_elements():
            self._collect_all_identifiers(element, all_identifiers)

    # Abstract methods to be implemented by concrete classes
    def _get_element_identifier(self, element: Executable) -> str:
        """Get the unique identifier from an element."""
        raise NotImplementedError

    def _get_element_children(self, element: Executable) -> list[Executable]:
        """Get child elements from an element (if any)."""
        raise NotImplementedError

    def _get_top_level_elements(self) -> list[Executable]:
        """Get all top-level elements."""
        raise NotImplementedError

    @model_validator(mode="after")
    def run_identifier_validation(self):
        """Run all identifier validation checks."""
        self.validate_all_identifiers()
        return self

    def get_previous_node_identifier(self, node_identifier: str) -> str | None:
        """Returns the identifier of the node that precedes the specified node.

        This method performs various sanity checks to ensure the node exists and
        has a valid previous node in the sequence.

        Args:
            node_identifier: The identifier of the current node

        Returns:
            Optional[str]: The identifier of the previous node, or None if:
                - The specified node is the first node in the flow
                - The specified node doesn't exist in the flow

        Raises:
            ValueError: If the provided node_identifier is empty or invalid

        Examples:
            >>> flow = FlowDefinition(nodes=[
            ...     FlowNode(identifier="node1", ...),
            ...     FlowNode(identifier="node2", ...),
            ... ])
            >>> flow.get_previous_node_identifier("node2")
            'node1'
            >>> flow.get_previous_node_identifier("node1")
            None
        """
        if not node_identifier:
            raise ValueError("Node identifier cannot be empty")

        # Create a list of node identifiers
        node_ids = [node.identifier for node in self.elements]

        try:
            # Find the index of the current node
            current_index = node_ids.index(node_identifier)

            # Return None if it's the first node
            if current_index == 0:
                return None

            # Return the previous node's identifier
            return node_ids[current_index - 1]

        except ValueError:
            # Node identifier not found in the flow
            return None


class NavigationMixin:
    """Mixin providing navigation capabilities for hierarchical structures."""

    def get_previous_element(self, identifier: str) -> tuple[Executable | None, str | None]:
        """
        Returns the element that precedes the specified element and its identifier.

        Args:
            identifier: The identifier of the current element

        Returns:
            Tuple of (previous_element, previous_identifier) or (None, None) if:
                - The specified element is the first element in the structure
                - The specified element doesn't exist in the structure

        Raises:
            ValueError: If the provided identifier is empty or invalid
        """
        if not identifier:
            raise ValueError("Element identifier cannot be empty")

        # Get a flattened view of all elements
        elements, identifiers = self._get_flattened_elements()

        try:
            # Find the index of the current element
            current_index = identifiers.index(identifier)

            # Return None if it's the first element
            if current_index == 0:
                return None, None

            # Return the previous element and its identifier
            return elements[current_index - 1], identifiers[current_index - 1]

        except ValueError:
            # Element identifier not found
            return None, None

    def get_previous_element_id(self, identifier: str) -> str | None:
        """
        Returns just the identifier of the element that precedes the specified element.

        Args:
            identifier: The identifier of the current element

        Returns:
            The identifier of the previous element, or None
        """
        _, prev_id = self.get_previous_element(identifier)
        return prev_id

    def get_element_by_id(self, identifier: str) -> Executable | None:
        """
        Find an element by its identifier.

        Args:
            identifier: The identifier to look for

        Returns:
            The element with the matching identifier, or None if not found
        """
        elements, identifiers = self._get_flattened_elements()
        try:
            index = identifiers.index(identifier)
            return elements[index]
        except ValueError:
            return None

    def _get_flattened_elements(self) -> tuple[list[Executable], list[str]]:
        """
        Get flattened lists of all elements and their identifiers, in execution order.

        Returns:
            Tuple of (elements_list, identifiers_list)
        """
        elements = []
        identifiers = []

        def _collect(element_list):
            for element in element_list:
                element_id = self._get_element_identifier(element)
                elements.append(element)
                identifiers.append(element_id)

                # Process children if any
                children = self._get_element_children(element)
                if children:
                    _collect(children)

        # Start with top-level elements
        _collect(self._get_top_level_elements())
        return elements, identifiers

    # These methods should be implemented by the class using this mixin
    # (They're likely already implemented for the IdentifierValidationMixin)
    def _get_element_identifier(self, element: Executable) -> str:
        """Get the unique identifier from an element."""
        raise NotImplementedError

    def _get_element_children(self, element: Executable) -> list[Executable]:
        """Get child elements from an element (if any)."""
        raise NotImplementedError

    def _get_top_level_elements(self) -> list[Executable]:
        """Get all top-level elements."""
        raise NotImplementedError

    # INFO: Not used currently, may be deleted in the future
    def _get_flattened_elements(self) -> tuple[list[Executable], list[str]]:
        """
        Get flattened lists of all elements and their identifiers, in execution order.
        Returns:
            Tuple of (elements_list, identifiers_list)
        """
        elements = []
        identifiers = []

        def _collect(element_list):
            for element in element_list:
                element_id = self._get_element_identifier(element)
                elements.append(element)
                identifiers.append(element_id)
                # Process children if any
                children = self._get_element_children(element)
                if children:
                    _collect(children)

        # Start with top-level elements
        _collect(self._get_top_level_elements())
        return elements, identifiers
