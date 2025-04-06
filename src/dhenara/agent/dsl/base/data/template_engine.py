import operator
import re
from collections.abc import Callable
from re import Pattern
from string import Template as StringTemplate
from typing import Any, Literal, TypeVar

T = TypeVar("T")


class TemplateEngine:
    """
    Unified template engine supporting both standard variable substitution and complex expressions.

    Features:
    1. standard mode: Basic $variable and ${variable} substitution like Python's string.Template
    2. Expression mode: Advanced ${...} syntax with:
       - Dot notation for nested properties (obj.property)
       - Array/list indexing (items[0])
       - Operators (>, <, ==, ||, &&, etc.)
       - Python expression evaluation (py:...)

    Examples:
        # Standard substitution (like string.Template)
        TemplateEngine.render_template("Hello $name", {"name": "World"}, mode="standard")
        # Output: "Hello World"

        # Expression mode with property access
        TemplateEngine.render_template("Count: ${data.count}", {"data": {"count": 42}})
        # Output: "Count: 42"

        # Expression mode with operators
        TemplateEngine.render_template("Result: ${value > 10}", {"value": 15})
        # Output: "Result: True"
    """

    # Regex patterns
    EXPR_PATTERN: Pattern = re.compile(r"\${([^}]+)}")
    INDEX_PATTERN: Pattern = re.compile(r"(.*)\[(\d+)\]")

    # Supported operators and their functions
    OPERATORS: dict[str, Callable[[Any, Any], Any]] = {
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
    SAFE_GLOBALS: dict[str, Callable] = {
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
        "sorted": sorted,
        "enumerate": enumerate,
        "zip": zip,
        "range": range,
    }

    @classmethod
    def render_template(
        cls,
        template: str,
        variables: dict[str, Any],
        mode: Literal["standard", "expression"] = "expression",
    ) -> str:
        """
        Render a template using either standard substitution or expression evaluation.

        Args:
            template: Template string
            variables: Variables for substitution/evaluation
            mode: "standard" for basic substitution, "expression" for advanced evaluation

        Returns:
            Rendered template string

        Examples:
            >>> TemplateEngine.render_template("Hello ${name}", {"name": "World"})
            'Hello World'
            >>> TemplateEngine.render_template("Status: ${online || 'offline'}", {"online": None})
            'Status: offline'
        """
        if not template:
            return template

        if mode == "standard":
            return cls.standard_substitute(template, variables)
        else:
            return cls.parse_and_evaluate(template, variables)

    @classmethod
    def standard_substitute(cls, template_str: str, variables: dict[str, Any]) -> str:
        """
        Perform standard variable substitution similar to string.Template.

        Args:
            template_str: Template string with $var or ${var} placeholders
            variables: Dictionary of variable values

        Returns:
            String with variables substituted

        Examples:
            >>> TemplateEngine.standard_substitute("Hello $name", {"name": "World"})
            'Hello World'
            >>> TemplateEngine.standard_substitute("${greeting} $name", {"greeting": "Hi", "name": "Alice"})
            'Hi Alice'
        """
        if not template_str:
            return template_str

        try:
            return StringTemplate(template_str).safe_substitute(variables)
        except Exception as e:
            return f"Error in template substitution: {e!s}"

    @staticmethod
    def _apply_word_limit(text: str, max_words: int | None) -> str:
        """
        Apply word limit to text if specified.

        Args:
            text: The text to limit
            max_words: Maximum number of words to include

        Returns:
            Text limited to the specified number of words
        """
        if max_words and text:
            words = text.split()
            return " ".join(words[:max_words])
        return text

    @classmethod
    def parse_and_evaluate(cls, template: str, variables: dict[str, Any]) -> str:
        """
        Parse expressions in the template and evaluate them against the variables.

        Args:
            template: Template string with ${...} expressions
            variables: Dictionary of variables accessible to the expressions

        Returns:
            Evaluated template with expressions replaced by their string values
        """
        if not template:
            return template

        def replace_expr(match: re.Match) -> str:
            expr = match.group(1).strip()
            try:
                result = cls._evaluate_expression(expr, variables)
                return str(result) if result is not None else ""
            except Exception as e:
                return f"Error: {e!s}"

        return cls.EXPR_PATTERN.sub(replace_expr, template)

    @classmethod
    def evaluate_single_expression(cls, expr_template: str, variables: dict[str, Any]) -> Any:
        """
        Evaluate a single expression and return the raw result without string conversion.

        Args:
            expr_template: Expression template like "${...}"
            variables: Dictionary of variables accessible to the expressions

        Returns:
            Raw result of evaluating the expression, preserving its type
        """
        if not expr_template:
            return expr_template

        # Extract the expression from ${...}
        match = cls.EXPR_PATTERN.search(expr_template)
        if match:
            expr = match.group(1).strip()
            try:
                return cls._evaluate_expression(expr, variables)
            except Exception as e:
                return f"Error: {e!s}"

        # If no expression found, return the template unchanged
        return expr_template

    @classmethod
    def _evaluate_expression(cls, expr: str, variables: dict[str, Any]) -> Any:
        """
        Evaluate a single expression against the variables.

        Args:
            expr: Expression string to evaluate
            variables: Dictionary of variables for evaluation

        Returns:
            Evaluated result of the expression

        Raises:
            ValueError: If there's an error evaluating a Python expression
        """
        # Python expression evaluation (advanced feature)
        if expr.startswith("py:"):
            return cls._evaluate_python_expression(expr[3:], variables)

        # Handle binary operators
        for op_text, op_func in cls.OPERATORS.items():
            if op_text in expr:
                # Split on operator, accounting for whitespace
                parts = expr.split(op_text, 1)
                left = cls._evaluate_expression(parts[0].strip(), variables)
                right = cls._evaluate_expression(parts[1].strip(), variables)
                return op_func(left, right)

        # Handle property access with dot notation and indexing
        return cls._get_value_from_path(expr, variables)

    @classmethod
    def _get_value_from_path(cls, path: str, variables: dict[str, Any]) -> Any:
        """
        Get a value from a dot-notation path with support for indexing.

        Examples:
            - "node1.data" - Gets the 'data' field from the result of node1
            - "node1.data.items[0]" - Gets the first item in the items array

        Args:
            path: Dot-notation path string
            variables: variables dictionary

        Returns:
            Value at the specified path or None if not found
        """
        if not path or not path.strip():
            return None

        path = path.strip()
        parts = path.split(".")

        # Start with the first part
        if parts[0] not in variables:
            return None

        current = variables[parts[0]]

        # Navigate through the parts
        for part in parts[1:]:
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

        Args:
            obj: Object to access property from
            name: Property name

        Returns:
            Property value or None if not found
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
    def _evaluate_python_expression(cls, expr: str, variables: dict[str, Any]) -> Any:
        """
        Evaluate a Python expression with safety constraints.

        Only a limited set of built-in functions are available.

        Args:
            expr: Python expression string
            variables: Variables for evaluation

        Returns:
            Result of evaluating the expression

        Raises:
            ValueError: If there's an error during evaluation
        """
        try:
            # Create a safe execution environment
            return eval(expr, {"__builtins__": cls.SAFE_GLOBALS}, variables)
        except Exception as e:
            raise ValueError(f"Error evaluating Python expression: {e!s}")


# TODO: Test  document and delete below
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
