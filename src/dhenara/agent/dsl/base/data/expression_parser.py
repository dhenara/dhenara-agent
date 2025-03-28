import operator
import re
from typing import Any

from dhenara.ai.types.genai.dhenara.request.data import Prompt, PromptText


class ExpressionParser:
    """Parser for expressions in ${...} syntax with support for dot notation, operators, and indexing."""

    # Regex to find expressions within ${...}
    EXPR_PATTERN = re.compile(r"\${([^}]+)}")

    # Regex to identify array/list indexing
    INDEX_PATTERN = re.compile(r"(.*)\[(\d+)\]")

    # Supported operators and their functions
    OPERATORS = {
        "||": lambda x, y: x if x is not None else y,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
        "==": operator.eq,
        "!=": operator.ne,
        "&&": lambda x, y: x and y,
    }

    # Safe globals for Python expression evaluation
    SAFE_GLOBALS = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "sum": sum,
        "min": min,
        "max": max,
        "all": all,
        "any": any,
    }

    @classmethod
    def prompt_to_text(
        cls,
        prompt: str | Prompt,
        parser_context: dict | None = None,
        max_words: int | None = None,
        max_words_file: int | None = None,
        **kwargs,
    ) -> str:
        if parser_context is None:
            parser_context = {}

        if isinstance(prompt, str):
            template_text = prompt.text
            parsed_text = cls.parse_and_evaluate(template_text, parser_context)
            formatted_text = parsed_text

        elif isinstance(prompt, Prompt):
            if isinstance(prompt.text, PromptText):
                if prompt.text.content:
                    template_text = prompt.text.content.get_content()
                    parsed_text = cls.parse_and_evaluate(template_text, parser_context)
                    formatted_text = parsed_text
                else:
                    var_dict = prompt.text.template.variables.copy()
                    var_dict.update(**kwargs)

                    template_text = prompt.text.template.text
                    parsed_text = cls.parse_and_evaluate(template_text, parser_context)

                    _temp = prompt.text.template.model_copy()
                    _temp.text = parsed_text
                    _temp.disable_checks = False
                    formatted_text = _temp.format(**kwargs)

            elif isinstance(prompt.text, str):
                template_text = prompt.text
                parsed_text = cls.parse_and_evaluate(template_text, parser_context)
                formatted_text = parsed_text
            else:
                raise ValueError(f"prompt_to_text: unknown prompt.text type {type(prompt.text)}")

        else:
            raise ValueError(f"prompt_to_text: unknown prompt type {type(prompt)}")

        if max_words:
            words = formatted_text.split()
            formatted_text = " ".join(words[:max_words])

        return formatted_text

    @classmethod
    def parse_and_evaluate(cls, template: str, context: dict[str, Any]) -> str:
        """
        Parse expressions in the template and evaluate them against the context.

        Args:
            template: Template string with ${...} expressions
            context: Dictionary of variables accessible to the expressions

        Returns:
            Evaluated template with expressions replaced by their values
        """
        if not template:
            return template

        def replace_expr(match):
            expr = match.group(1).strip()
            try:
                result = cls._evaluate_expression(expr, context)
                return str(result) if result is not None else ""
            except Exception as e:
                return f"Error: {e!s}"

        parsed = cls.EXPR_PATTERN.sub(replace_expr, template)
        return parsed

    @classmethod
    def _evaluate_expression(cls, expr: str, context: dict[str, Any]) -> Any:
        """Evaluate a single expression against the context."""
        # First check if it's a Python expression (advanced feature)
        if expr.startswith("py:"):
            return cls._evaluate_python_expression(expr[3:], context)

        # Handle binary operators
        for op_text, op_func in cls.OPERATORS.items():
            if op_text in expr:
                # Split on operator, accounting for whitespace
                parts = expr.split(op_text, 1)
                left = cls._evaluate_expression(parts[0].strip(), context)
                right = cls._evaluate_expression(parts[1].strip(), context)
                return op_func(left, right)

        # Handle property access with dot notation and indexing
        return cls._get_value_from_path(expr, context)

    @classmethod
    def _get_value_from_path(cls, path: str, context: dict[str, Any]) -> Any:
        """
        Get a value from a dot-notation path with support for indexing.

        Examples:
            - "node1.data" - Gets the 'data' field from the result of node1
            - "node1.data.items[0]" - Gets the first item in the items array
        """
        if not path or not path.strip():
            return None

        path = path.strip()
        parts = path.split(".")

        # Start with the first part
        if parts[0] not in context:
            return None

        current = context[parts[0]]

        # Navigate through the parts
        for i, part in enumerate(parts[1:], 1):  # noqa: B007
            # Check for array indexing
            index_match = cls.INDEX_PATTERN.match(part)
            if index_match:
                # Split into name and index
                name, idx_str = index_match.groups()
                idx = int(idx_str)

                # Get the object first if name is provided
                if name:
                    current = cls._access_property(current, name)
                    if current is None:
                        return None

                # Access by index
                if isinstance(current, (list, tuple)) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                # Regular property access
                current = cls._access_property(current, part)
                if current is None:
                    return None

        return current

    @staticmethod
    def _access_property(obj: Any, name: str) -> Any:
        """
        Access a property from an object, supporting both
        dictionary access and attribute access.
        """
        if obj is None:
            return None

        # Try dictionary access first
        if isinstance(obj, dict) and name in obj:
            return obj[name]

        # Then try attribute access
        if hasattr(obj, name):
            return getattr(obj, name)

        return None

    @classmethod
    def _evaluate_python_expression(cls, expr: str, context: dict[str, Any]) -> Any:
        """
        Evaluate a Python expression with safety constraints.

        Only a limited set of built-in functions are available.
        """
        try:
            # Create a safe execution environment
            return eval(expr, {"__builtins__": cls.SAFE_GLOBALS}, context)
        except Exception as e:
            raise ValueError(f"Error evaluating Python expression: {e}")


"""
Usage Examples:
# Context with nested data
context = {
    "node1": {
        "data": {
            "items": [{"name": "Item 1"}, {"name": "Item 2"}],
            "count": 2
        }
    },
    "node2": {
        "result": True
    }
}

# Basic property access
ExpressionParser.parse_and_evaluate("Result is ${node1.data.count}", context)
# Output: "Result is 2"

# Array indexing
ExpressionParser.parse_and_evaluate("First item: ${node1.data.items[0].name}", context)
# Output: "First item: Item 1"

# Conditional operator
ExpressionParser.parse_and_evaluate("Status: ${node1.data.count > 1 && node2.result}", context)
# Output: "Status: True"

# Fallback operator
ExpressionParser.parse_and_evaluate("Value: ${node1.missing || node1.data.count}", context)
# Output: "Value: 2"

# Python expression (advanced)
ExpressionParser.parse_and_evaluate("Total: ${py:sum([item['name'].count('Item') for item in node1.data.items])}", context)
# Output: "Total: 2"

"""  # noqa: E501, W505
