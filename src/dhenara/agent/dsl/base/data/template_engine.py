import logging
import operator
import re
import uuid
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
    3. Hierarchical access with $hier{...} to access execution context elements

    Escape sequences:
    - Use $$var{} to output a literal "$var{}" string
    - Use $$expr{} to output a literal "$expr{}" string
    - Use $$hier{} to output a literal "$hier{}" string

    Examples:
        # Variable substitution
        TemplateEngine.render_template("Hello $var{name}", {"name": "World"})
        # Output: "Hello World"

        # Expression mode with property access
        TemplateEngine.render_template("Count: $expr{data.count}", {"data": {"count": 42}})
        # Output: "Count: 42"

        # Hierarchical access with nested expressions
        TemplateEngine.render_template("Task: $expr{$hier{planner.plan_generator}.structured.task_name}", {})
        # Output: "Task: Create project plan"

        # Python expression with hierarchical access
        TemplateEngine.render_template("Valid: $expr{py: $hier{planner.plan_generator}.structured is not None}", {})
        # Output: "Valid: True"
    """

    EXPR_PATTERN: Pattern = re.compile(r"\$expr{([^}]+)}")
    VAR_PATTERN: Pattern = re.compile(r"\$var{([^}]+)}")
    HIER_PATTERN: Pattern = re.compile(r"\$hier{([^}]+)}")
    ESCAPED_EXPR_PATTERN: Pattern = re.compile(r"\$\$expr{([^}]+)}")
    ESCAPED_VAR_PATTERN: Pattern = re.compile(r"\$\$var{([^}]+)}")
    ESCAPED_HIER_PATTERN: Pattern = re.compile(r"\$\$hier{([^}]+)}")
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
    OPERATOR_PRECEDENCE = [
        ["==", "!=", ">", "<", ">=", "<="],  # Comparison operators
        ["&&"],  # Logical AND
        ["||"],  # Logical OR
    ]

    # Safe globals for Python expression evaluation
    SAFE_GLOBALS: dict[str, Callable] = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "sum": sum,
        "min": min,
        "max": max,
        "all": all,
        "any": any,
        "filter": filter,
        "sorted": sorted,
        "enumerate": enumerate,
        "zip": zip,
        "range": range,
        "isinstance": isinstance,
        "getattr": getattr,
        "hasattr": hasattr,
        "map": map,
    }

    @classmethod
    def render_template(
        cls,
        template: str,
        variables: dict[str, Any],
        execution_context: Optional["ExecutionContext"] = None,
        mode: Literal["standard", "expression"] = "expression",
        max_words: int | None = None,
        debug_mode: bool = False,
    ) -> str:
        """
        Render a string template with context support.

        This function evaluates template expressions and returns a string that replaces the
        expressions with their STRING representation.
        Used for String Template evaluation.

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

        # Process $expr{}/ $hier{} only in expression mode
        if mode == "expression":
            # Create a copy of variables to avoid modifying the original
            working_vars = variables.copy()

            # Process hierarchical references first, replacing with placeholders
            template, placeholder_vars = cls._process_hier_with_placeholders(
                template=template,
                variables=working_vars,
                execution_context=execution_context,
                debug_mode=debug_mode,
            )

            # Add placeholder variables to working variables
            working_vars.update(placeholder_vars)

            # Process expressions with the enhanced variables
            template = cls._process_expr_substitutions(
                template=template,
                variables=working_vars,
                execution_context=execution_context,
                result_as_string=True,
                debug_mode=debug_mode,
            )

        # Apply word limit if specified
        return cls._apply_word_limit(template, max_words)

    @classmethod
    def evaluate_template(
        cls,
        expr_template: str,
        variables: dict[str, Any],
        execution_context: Optional["ExecutionContext"] = None,
        debug_mode: bool = False,
    ) -> Any:
        """
        Evaluate template expression and return the raw result of evaluating the expression,
        preserving its type without string conversion.
        Used for ObjectTemplate evaluation.
        """
        if not expr_template:
            return expr_template

        # First handle escape sequences
        expr_template = cls._process_escape_sequences(expr_template)

        # Create a copy of variables to avoid modifying the original
        working_vars = variables.copy()

        # Process hierarchical references first, replacing with placeholders
        expr_template, placeholder_vars = cls._process_hier_with_placeholders(
            template=expr_template,
            variables=working_vars,
            execution_context=execution_context,
            debug_mode=debug_mode,
        )

        # Add placeholder variables to working variables
        working_vars.update(placeholder_vars)

        # Process expressions with the enhanced variables
        return cls._process_expr_substitutions(
            template=expr_template,
            variables=working_vars,
            execution_context=execution_context,
            result_as_string=False,
            debug_mode=debug_mode,
        )

    @classmethod
    def _process_escape_sequences(cls, template: str) -> str:
        """Process escape sequences ($$ to $) in templates."""
        if not template:
            return template

        # Replace $$expr{} with $expr{}
        template = cls.ESCAPED_EXPR_PATTERN.sub(r"$expr{\1}", template)

        # Replace $$var{} with $var{}
        template = cls.ESCAPED_VAR_PATTERN.sub(r"$var{\1}", template)

        # Replace $$hier{} with $hier{}
        template = cls.ESCAPED_HIER_PATTERN.sub(r"$hier{\1}", template)

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
    def _process_hier_with_placeholders(
        cls,
        template: str,
        variables: dict[str, Any],
        execution_context: Optional["ExecutionContext"] = None,
        debug_mode: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """
        Process $hier{} references by replacing them with unique placeholders.

        Returns:
            tuple: (modified template string, dictionary of placeholder variables)
        """
        if not template:
            return template, {}

        placeholder_vars = {}

        def replace_hier(match: re.Match) -> str:
            hier_path = match.group(1).strip()
            try:
                # Generate a unique placeholder variable name
                placeholder = f"__hier_placeholder_{uuid.uuid4().hex[:8]}__"

                # Resolve the hierarchical path
                result = cls._resolve_hierarchical_path_with_exe_result(hier_path, execution_context)

                # Store the result with the placeholder name
                placeholder_vars[placeholder] = result

                # Return the placeholder variable name
                return placeholder

            except Exception as e:
                logger.error(f"Error processing hierarchical path '{hier_path}': {e}")
                # Return a placeholder for the error to avoid breaking the template
                error_placeholder = f"__hier_error_{uuid.uuid4().hex[:8]}__"
                placeholder_vars[error_placeholder] = f"Error: {e!s}"
                return error_placeholder

        # Replace all $hier{} expressions with placeholders
        modified_template = cls.HIER_PATTERN.sub(replace_hier, template)

        return modified_template, placeholder_vars

    @classmethod
    def _process_expr_substitutions(
        cls,
        template: str,
        variables: dict[str, Any],
        execution_context: Optional["ExecutionContext"] = None,
        result_as_string: bool = False,
        debug_mode: bool = False,
    ) -> Any:
        """
        Process expressions in a template with context support.
        Returns the result directly if there's a single expression,
        otherwise returns the string with substitutions.
        """
        if not template:
            return template

        # For a single expression that encompasses the entire template,
        # evaluate and return the raw result
        if not result_as_string:
            full_match = cls.EXPR_PATTERN.fullmatch(template)
            if full_match:
                expr = full_match.group(1).strip()
                try:
                    return cls._evaluate_expression(
                        expr,
                        variables,
                        execution_context,
                        debug_mode=debug_mode,
                    )
                except Exception as e:
                    logger.error(f"Error evaluating expression '{expr}': {e}")
                    return f"Error: {e!s}"

        # For multiple expressions or mixing with text, perform substitutions
        def replace_expr(match: re.Match) -> str:
            expr = match.group(1).strip()
            try:
                result = cls._evaluate_expression(
                    expr,
                    variables,
                    execution_context,
                    debug_mode=debug_mode,
                )

                if isinstance(result, list):
                    processed_list = [
                        listitem.model_dump() if hasattr(listitem, "model_dump") else listitem for listitem in result
                    ]
                    result = processed_list
                elif isinstance(result, dict):
                    processed_dict = {k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in result.items()}
                    result = processed_dict
                elif hasattr(result, "model_dump"):
                    result = result.model_dump()
                else:
                    pass

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
    def _evaluate_expression(
        cls,
        expr: str,
        variables: dict[str, Any],
        execution_context: ExecutionContext,
        debug_mode: bool = False,
    ) -> Any:
        """
        Evaluate an expression  with enhanced support for brackets and complex operations.
        """
        # Update variables with the loop/conditional variables in context
        variables.update(execution_context.get_context_variables_hierarchical())

        # If we are evaluating a Python expression, do it immediately without further pre-processing
        # 0. Handle Python expressions
        if expr.startswith("py:"):
            _pyexpr = expr[3:].strip()

            # ---------------- Attribute-style access in Python: BEGINS -------
            _pyexpr, eval_vars = cls._process_object_path_with_hier_variables(
                expr_with_hier_vars=_pyexpr,
                variables=variables,
                debug_mode=debug_mode,
            )
            # ---------------- Attribute-style access in Python: ENDS -------

            # Evaluate the modified Python expression
            try:
                return eval(_pyexpr, {"__builtins__": cls.SAFE_GLOBALS}, eval_vars)
                # logger.debug(f"Evaluated Python expression: {_pyexpr} = {result}")
            except Exception as e:
                logger.error(f"Error evaluating Python expression '{_pyexpr}': {e}")
                return f"Error: {e!s}"

        # 1. For non-python expressions, first process bracketed subexpressions
        if debug_mode:
            logger.debug(f"_evaluate_expression: expr={expr}, variables={variables.keys()}")

        bracket_pattern = re.compile(r"\(([^()]*)\)")
        while True:
            match = bracket_pattern.search(expr)
            if not match:
                break
            inner_expr = match.group(1)
            inner_result = cls._evaluate_expression(inner_expr, variables, execution_context, debug_mode=debug_mode)
            expr = expr[: match.start()] + str(inner_result) + expr[match.end() :]

        # 2. Handle binary operators by precedence
        for precedence_group in cls.OPERATOR_PRECEDENCE:
            for op_text in precedence_group:
                op_func = cls.OPERATORS[op_text]
                if op_text in expr:
                    parts = expr.split(op_text, 1)
                    left = cls._evaluate_expression(
                        parts[0].strip(),
                        variables,
                        execution_context,
                        debug_mode=debug_mode,
                    )
                    right = cls._evaluate_expression(
                        parts[1].strip(),
                        variables,
                        execution_context,
                        debug_mode=debug_mode,
                    )
                    return op_func(left, right)

        # 3. Handle literal values before attempting variable resolution
        literal_value = cls._try_parse_literal(expr)
        if literal_value is not None:
            return literal_value

        # 4. Check if it's a direct variable reference
        if expr in variables:
            return variables[expr]

        # 5.Handle path resolution for nested properties
        if "." in expr:
            return cls._resolve_object_path(expr, variables)

        # Not found - return None
        return None

    @classmethod
    def _try_parse_literal(cls, expr: str) -> Any:
        """
        Attempt to parse a string as a literal value (number, boolean, null).
        Returns the parsed value if successful, otherwise None.
        """
        expr = expr.strip()

        # Handle numeric literals
        try:
            # Try integer first
            return int(expr)
        except ValueError:
            try:
                # Then try float
                return float(expr)
            except ValueError:
                pass

        # Handle boolean literals
        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False

        # Handle null/None
        if expr.lower() in ("null", "none"):
            return None

        # Handle quoted string literals
        if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # Not a recognized literal
        return None

    @classmethod
    def _process_object_path_with_hier_variables(
        cls,
        expr_with_hier_vars: str,
        variables: dict[str, Any],
        debug_mode: bool = False,
    ) -> tuple[str, dict]:
        # ---------------- Attribute-style access in Python: BEGINS -------
        #
        # Below part was required only to allow attribute-style access to a dict INSIDE the execution result
        # Example:
        #   1. expression="$expr{ $hier{planner.plan_generator}.outcome.structured.implementation_tasks }",
        #   2. expression="$expr{py: $hier{planner.plan_generator}.outcome.structured['implementation_tasks'] }"
        #   3. expression="$expr{py: $hier{planner.plan_generator}.outcome.structured.implementation_tasks }",
        #
        # In a normal $expr evaluation like in Eg:1, we take care of attribute-style (dotted) access of execution
        # result properties.
        # But in python expression $expr{py: }, it won't work, thus we need to access the individual properties
        # as if like in a python statement, structured['implementation_tasks']
        # Below fixes are to enables same attribute-style (dot) access for :py expressions as well
        #

        # Look for patterns with hierarchical placeholders followed by dot notation
        # This pattern matches "__hier_placeholder_XXXX__.something.else"

        # hier_path_pattern = re.compile(r"(__hier_placeholder_[a-f0-9]{8}__(?:\.[a-zA-Z0-9_]+)*\.[a-zA-Z0-9_]+)")
        ## Find all matches in the Python expression
        # matches = hier_path_pattern.findall(expr_with_hier_vars)

        # Create evaluation variables by copying the original
        eval_vars = variables.copy()

        # Find all hierarchical placeholder patterns in the expression
        matches = []
        # Find placeholders that might include method calls
        for var_name in variables:
            if var_name.startswith("__hier_placeholder_") and var_name.endswith("__"):
                # For each placeholder, look for it plus dot notation in the expression
                path_pattern = re.compile(f"{re.escape(var_name)}(?:\\.[a-zA-Z0-9_]+)+")
                matches.extend(match.group(0) for match in path_pattern.finditer(expr_with_hier_vars))

        # Process each match
        for match in matches:
            try:
                # Resolve the full path using our path resolver
                resolved_value = cls._resolve_object_path(match, variables, debug_mode=debug_mode)

                # Create a temporary variable for this resolved value
                temp_var_name = f"__temp_var_{uuid.uuid4().hex[:8]}__"
                eval_vars[temp_var_name] = resolved_value

                # Replace the path with the temporary variable in the expression
                expr_with_hier_vars = expr_with_hier_vars.replace(match, temp_var_name)

                if debug_mode:
                    logger.debug(f"Processed path {match} in Python expression and assigned to {temp_var_name}")

            except Exception as e:  # noqa: PERF203
                logger.error(f"Error resolving path '{match}': {e}")

        return expr_with_hier_vars, eval_vars

    @classmethod
    def _resolve_object_path(
        cls,
        path: str,
        variables: dict[str, Any],
        debug_mode: bool = False,
    ) -> Any:
        """
        Resolve a dot-notation path within variables.
        E.g., "user.profile.name" will access variables["user"]["profile"]["name"]
        """
        if not path or not variables:
            return None

        parts = path.split(".")
        if not parts:
            return None

        # Start with the first component
        if parts[0] not in variables:
            return None

        current = variables[parts[0]]

        # Navigate through the path
        for part in parts[1:]:
            # Handle array/list indexing with [n] syntax
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
                if isinstance(current, (list, tuple)):
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return None
                elif isinstance(current, dict) and str(idx) in current:
                    current = current[str(idx)]
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
    def _resolve_hierarchical_path_with_exe_result(
        cls,
        path_str: str,
        execution_context: Optional["ExecutionContext"] = None,
    ) -> Any:
        """
        Resolve a hierarchical path expression in the execution context.

        The path format is "component1.component2.node_id" where:
        - All parts except the last represent the component hierarchy
        - The last part is a node ID that has execution results

        Args:
            path: Hierarchical path like "planner.plan_generator"
            execution_context: Current execution context

        Returns:
            The resolved node execution result or None if not found
        """
        if not execution_context:
            return None
        # Parse the path
        path_str_parts = path_str.split(".")
        if not path_str_parts:
            return None

        # First look for a direct node reference (only one part in the path)
        if len(path_str_parts) == 1:
            target_node_id = path_str_parts[0]

            # Start from current context and traverse up through parents
            current_ctx = execution_context
            while current_ctx:
                if target_node_id in current_ctx.execution_results:
                    return current_ctx.execution_results[target_node_id]
                current_ctx = current_ctx.parent

            logger.error(
                f"resolve_hierarchical_path: Failed to find node_id {target_node_id} "
                "in context hierarchy while a direct node_id is given"
            )
            return None

        # For hierarchical paths, separate component path and target node

        # The path doesn't necessarly be the full path, it can be a relative one from the current context.
        # So, first build the full hierarchy path of the incoming path
        # Now its sure that the incoming path is referring to a component hierarcy

        target_node_id = path_str_parts[-1]
        component_path_parts = path_str_parts[:-1]
        component_path = ".".join(component_path_parts)

        execution_result = None

        execution_context_registry = execution_context.run_context.execution_context_registry
        fetch_context = True if execution_context_registry.enable_caching else False

        logger.debug(f"Looking for cached context for path {path_str}")
        component_path, component_ctx = execution_context_registry.lookup_context_by_partial_path(
            partial_path=component_path,
            current_context_path=execution_context.get_hierarchy_path(path_joiner="."),
            fetch_context=fetch_context,
        )

        if not (component_path or component_ctx):
            logger.error(f"No match found for {component_path}")
            return None

        # If execution_context caching is enabled, navigate through the execution context
        if fetch_context:
            if component_ctx is None:
                logger.error(f"Failed to find context for component path {component_path}")
                return None

            if target_node_id in component_ctx.execution_results:
                execution_result = component_ctx.execution_results[target_node_id]
                return execution_result
            else:
                logger.error(f"Failed to find node_id {target_node_id} in context for component path {component_path}")

        # If not found in the context hierarchy, attempt to load from filesystem
        results = execution_context.run_context.load_previous_run_execution_result_dict(
            hierarchy_path=component_path,
            is_component=False,
        )

        if results is None:
            return None

        if target_node_id in results:
            execution_result = component_ctx.execution_results[target_node_id]
            return execution_result
        else:
            logger.error(
                f"Failed to find node_id {target_node_id} in context for component path {component_path} via filesystem"
            )

        return None
