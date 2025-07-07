from typing import Any

from opentelemetry.trace import Span

from dhenara.agent.observability.tracing.data import (
    TracingAttribute,
)


class SpanAttributeManager:
    """Centralized manager for handling span attributes with consistent serialization and truncation."""

    def __init__(self, max_string_length: int = 4096, default_preview_length: int = 500):
        self.max_string_length = max_string_length
        self.default_preview_length = default_preview_length

    def extract_value(self, obj: Any, path: str) -> Any:
        """Extract a value from an object using dot notation path."""
        if not path or not obj:
            return None

        parts = path.split(".")
        current = obj

        for part in parts:
            # Handle array/list indexing
            if "[" in part and part.endswith("]"):
                attr_name, idx_str = part.split("[", 1)
                idx = int(idx_str[:-1])  # Remove the closing bracket

                if attr_name:
                    # Get the list/array first
                    if hasattr(current, attr_name):
                        current = getattr(current, attr_name)
                    elif isinstance(current, dict) and attr_name in current:
                        current = current[attr_name]
                    else:
                        return None

                # Then access by index
                if isinstance(current, (list, tuple)) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                # Regular attribute or dict key
                if hasattr(current, part):
                    current = getattr(current, part)
                elif isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None

        return current

    def truncate_string(self, value: str, max_length: int) -> str:
        """Truncate a string to max_length if needed."""
        if not isinstance(value, str):
            return value

        if len(value) <= max_length:
            return value

        return value[:max_length] + f"... [truncated, {len(value)} total chars]"

    def serialize_value(self, value: Any, max_length: int | None = None) -> Any:
        """
        Serialize and sanitize a value for OpenTelemetry spans.

        OpenTelemetry supports: str, bool, int, float, and sequences of these types.
        """
        # Handle None
        if value is None:
            return "None"

        # Handle basic types that OTel supports directly
        if isinstance(value, (bool, int, float)):
            return value

        # Handle strings with truncation
        if isinstance(value, str):
            effective_max_length = max_length or self.max_string_length
            return self.truncate_string(value, effective_max_length)

        # Handle lists and tuples - recursively serialize each item
        if isinstance(value, (list, tuple)):
            # Only serialize up to 10 items to avoid huge spans
            serialized = [self.serialize_value(item, max_length) for item in value[:10]]
            if len(value) > 10:
                serialized.append("... (truncated)")
            return serialized

        # Handle dictionaries
        if isinstance(value, dict):
            simplified = {}
            # Only include first 10 keys to avoid huge spans
            for i, (k, v) in enumerate(value.items()):
                if i >= 10:
                    simplified["..."] = "(truncated)"
                    break
                simplified[str(k)] = self.serialize_value(v, max_length)
            # Convert to string to ensure OTel compatibility
            dict_str = str(simplified)
            effective_max_length = max_length or self.max_string_length
            return self.truncate_string(dict_str, effective_max_length)

        # Handle Pydantic models (both v1 and v2)
        if hasattr(value, "model_dump") and callable(value.model_dump):
            try:
                return self.serialize_value(value.model_dump(), max_length)
            except Exception:
                pass

        if hasattr(value, "dict") and callable(value.dict):
            try:
                return self.serialize_value(value.dict(), max_length)
            except Exception:
                pass

        # For any other types, use string representation
        try:
            str_value = str(value)
            effective_max_length = max_length or self.max_string_length
            return self.truncate_string(str_value, effective_max_length)
        except Exception:
            return "<unprintable>"

    def _build_attribute_name(self, attribute: TracingAttribute, prefix: str | None = None) -> str:
        """Build the full attribute name with prefix."""
        if prefix:
            return f"dad.{attribute.group_name}.{prefix}.{attribute.name}"
        return f"dad.{attribute.group_name}.{attribute.name}"

    def add_attribute(
        self,
        span: Span,
        attribute: TracingAttribute,
        value: Any,
        prefix: str | None = None,
    ) -> None:
        """
        Add a single attribute to a span with proper processing.

        Args:
            span: The OpenTelemetry span
            attribute: TracingAttribute instance defining the attribute
            value: The value to add
            prefix: Optional prefix for the attribute name
        """
        if not isinstance(attribute, TracingAttribute):
            raise ValueError(
                f"attribute should be an instance of TracingAttribute, not {type(attribute)}. attribute={attribute}"
            )

        # Apply transformation if specified
        processed_value = value
        if attribute.transform and callable(attribute.transform):
            try:
                processed_value = attribute.transform(value)
            except Exception:
                # If transformation fails, use original value
                pass

        # Serialize the value with optional max_length
        serialized_value = self.serialize_value(processed_value, attribute.max_length)

        # Build attribute name and add to span
        attribute_name = self._build_attribute_name(attribute, prefix)
        span.set_attribute(attribute_name, serialized_value)

    def add_profile_attributes(
        self,
        span: Span,
        data_object: Any,
        attributes: list[TracingAttribute],
        prefix: str | None = None,
    ) -> None:
        """
        Add multiple attributes from a data object to a span based on tracing attribute definitions.

        Args:
            span: The OpenTelemetry span
            data_object: The object to extract values from
            attributes: List of TracingAttribute instances
            prefix: Optional prefix for all attribute names
        """
        for attribute in attributes:
            # Extract the value using the source path
            value = self.extract_value(data_object, attribute.source_path)

            # Skip if no value was found
            if value is None:
                continue

            # Use the unified add_attribute method
            self.add_attribute(span, attribute, value, prefix)


# Create a shared instance
span_attribute_manager = SpanAttributeManager()
