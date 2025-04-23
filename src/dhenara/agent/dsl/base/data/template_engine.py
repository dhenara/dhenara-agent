import logging
import operator
import re
from collections.abc import Callable
from re import Pattern
from typing import TYPE_CHECKING, Any, Literal, Optional, TypeVar

T = TypeVar("T")

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from dhenara.agent.dsl.base import ExecutionContext
else:
    ExecutionContext = Any

logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    Unified template engine supporting variable substitution and complex expressions.

    Features:
    1. Variable substitution with $var{variable}
    2. Expression evaluation with $expr{...} syntax with:
       - Dot notation for nested properties (obj.property)
       - Array/list indexing (items[0])
       - Operators (>, <, ==, ||, &&, etc.)
       - Python expression evaluation (py:...)

    Escape sequences:
    - Use $$var{} to output a literal "$var{}" string
    - Use $$expr{} to output a literal "$expr{}" string

    Examples:
        # Variable substitution
        TemplateEngine.render_template("Hello $var{name}", {"name": "World"})
        # Output: "Hello World"

        # Expression mode with property access
        TemplateEngine.render_template("Count: $expr{data.count}", {"data": {"count": 42}})
        # Output: "Count: 42"

        # Expression mode with operators
        TemplateEngine.render_template("Result: $expr{value > 10}", {"value": 15})
        # Output: "Result: True"

        # Escape sequences
        TemplateEngine.render_template("Literal: $$expr{not.evaluated}", {})
        # Output: "Literal: $expr{not.evaluated}"

        # Regular braces are left untouched
        TemplateEngine.render_template("Braces: {not.a.placeholder}", {})
        # Output: "Braces: {not.a.placeholder}"
    """

    # Regex patterns
    EXPR_PATTERN: Pattern = re.compile(r"\$expr{([^}]+)}")
    VAR_PATTERN: Pattern = re.compile(r"\$var{([^}]+)}")
    ESCAPED_EXPR_PATTERN: Pattern = re.compile(r"\$\$expr{([^}]+)}")
    ESCAPED_VAR_PATTERN: Pattern = re.compile(r"\$\$var{([^}]+)}")
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
        execution_context: Optional["ExecutionContext"] = None,
        mode: Literal["standard", "expression"] = "expression",
        max_words: int | None = None,
    ) -> str:
        """
        Render a string template with context support.

        Args:
            template: String template to render
            variables: Variables for substitution/evaluation
            execution_context: Execution context for node result resolution
            mode: Rendering mode
            max_words: Maximum number of words in output

        Returns:
            Rendered template string

        Examples:
            >>> TemplateEngine.render_template("Hello $var{name}", {"name": "World"})
            'Hello World'
            >>> TemplateEngine.render_template("Status: $expr{online || 'offline'}", {"online": None})
            'Status: offline'
            >>> TemplateEngine.render_template("Literal: $$expr{not.evaluated}", {})
            'Literal: $expr{not.evaluated}'
            >>> TemplateEngine.render_template("Braces: {just plain text}", {})
            'Braces: {just plain text}'
        """
        if not template:
            return template

        # Process escape sequences
        template = cls._process_escape_sequences(template)

        # Process $var{} regardless of mode
        template = cls._process_var_substitutions(template, variables)

        # Process $expr{} only in expression mode
        if mode == "expression":
            template = cls._process_expr_substitutions(template, variables, execution_context)

        # Apply word limit if specified
        return cls._apply_word_limit(template, max_words)

    @classmethod
    def _process_escape_sequences(cls, template: str) -> str:
        """
        Process escape sequences ($$var{} and $$expr{}) by replacing them
        with single $ versions.

        Args:
            template: Template string containing escape sequences

        Returns:
            String with escape sequences converted to their literal form
        """
        if not template:
            return template

        # Replace $$expr{} with $expr{}
        template = cls.ESCAPED_EXPR_PATTERN.sub(r"$expr{\1}", template)

        # Replace $$var{} with $var{}
        template = cls.ESCAPED_VAR_PATTERN.sub(r"$var{\1}", template)

        return template

    @classmethod
    def _process_var_substitutions(cls, template: str, variables: dict[str, Any]) -> str:
        """
        Process simple variable substitutions with $var{} syntax.

        Args:
            template: Template string containing $var{} patterns
            variables: Dictionary of variables for substitution

        Returns:
            String with variables substituted
        """
        if not template:
            return template

        def replace_var(match: re.Match) -> str:
            var_name = match.group(1).strip()
            if var_name in variables:
                value = variables[var_name]
                return str(value) if value is not None else ""
            return match.group(0)  # Return unchanged if variable not found

        return cls.VAR_PATTERN.sub(replace_var, template)

    @classmethod
    def _process_expr_substitutions(
        cls,
        template: str,
        variables: dict[str, Any],
        execution_context: Optional["ExecutionContext"] = None,
    ) -> str:
        """
        Process expressions in a template with context support, converting results to strings.

        Args:
            template: Template string containing expressions
            variables: Variables for evaluation
            execution_context: Execution context for node result resolution

        Returns:
            Template with expressions evaluated and converted to strings
        """
        if not template:
            return template

        def replace_expr(match: re.Match) -> str:
            expr = match.group(1).strip()
            try:
                # Evaluate the expression and convert result to string
                result = cls._evaluate_expression(expr, variables, execution_context)
                return str(result) if result is not None else ""
            except Exception as e:
                logger.error(f"Error evaluating expression '{expr}': {e}")
                return f"Error: {e!s}"

        return cls.EXPR_PATTERN.sub(replace_expr, template)

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
    def evaluate_single_expression(
        cls,
        expr_template: str,
        variables: dict[str, Any],
        execution_context: Optional["ExecutionContext"] = None,
    ) -> Any:
        """
        Evaluate a single expression and return the raw result without string conversion.
        Used primarily for ObjectTemplate evaluation.

        Args:
            expr_template: Expression template like "$expr{...}"
            variables: Dictionary of variables accessible to the expressions

        Returns:
            Raw result of evaluating the expression, preserving its type
        """
        if not expr_template:
            return expr_template

        # First handle escape sequences
        expr_template = cls._process_escape_sequences(expr_template)

        # Extract the expression from $expr{...}
        match = cls.EXPR_PATTERN.search(expr_template)
        if match:
            expr = match.group(1).strip()
            try:
                return cls._evaluate_expression(expr, variables, execution_context)
            except Exception as e:
                return f"Error: {e!s}"

        # If no expression found, return the template unchanged
        return expr_template  # Return the original template

    @classmethod
    def _evaluate_expression(
        cls,
        expr: str,
        variables: dict[str, Any],
        execution_context: Optional["ExecutionContext"] = None,
    ) -> Any:
        """
        Evaluate an expression with context support.

        Args:
            expr: Expression to evaluate
            variables: Variables for evaluation
            execution_context: Execution context for node result resolution

        Returns:
            Evaluated result with original type preserved
        """
        # Handle Python expressions
        if expr.startswith("py:"):
            return cls._evaluate_python_expression(expr[3:], variables)

        # Handle binary operators
        for op_text, op_func in cls.OPERATORS.items():
            if op_text in expr:
                parts = expr.split(op_text, 1)
                left = cls._evaluate_expression(parts[0].strip(), variables, execution_context)
                right = cls._evaluate_expression(parts[1].strip(), variables, execution_context)
                return op_func(left, right)

        # Handle path resolution
        return cls._get_value_from_path(expr, variables, execution_context)

    @classmethod
    def _get_value_from_path(
        cls,
        path: str,
        variables: dict[str, Any],
        execution_context: Optional["ExecutionContext"] = None,
    ) -> Any:
        """
        Get a value from a dot-notation path with hierarchical node resolution.

        Args:
            path: Dot-notation path
            variables: Variables dictionary
            execution_context: Execution context for node result resolution

        Returns:
            Value at the specified path or None if not found
        """
        if not path or not path.strip():
            return None

        path = path.strip()
        parts = path.split(".")
        first_part = parts[0]

        # First check in the variables dictionary
        if first_part in variables:
            current = variables[first_part]
        # Then try to resolve as a node result if execution context is available
        elif execution_context is not None:
            # Use the hierarchical node resolution method
            node_result = execution_context.get_context_variable_value_hierarchical(first_part)
            if node_result is not None:
                current = node_result
            else:
                return None
        else:
            # Not found in variables and no execution context
            return None

        # Navigate through remaining parts...
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
ExpressionParser.parse_and_evaluate("Result is $expr{node1.data.count}", context)
# Output: "Result is 2"

# Array indexing
ExpressionParser.parse_and_evaluate("First item: $expr{node1.data.items[0].name}", context)
# Output: "First item: Item 1"

# Conditional operator
ExpressionParser.parse_and_evaluate("Status: $expr{node1.data.count > 1 && node2.result}", context)
# Output: "Status: True"

# Fallback operator
ExpressionParser.parse_and_evaluate("Value: $expr{node1.missing || node1.data.count}", context)
# Output: "Value: 2"

# Python expression (advanced)
ExpressionParser.parse_and_evaluate("Total: $expr{py:sum([item['name'].count('Item') for item in node1.data.items])}", context)
# Output: "Total: 2"

"""  # noqa: E501, W505
