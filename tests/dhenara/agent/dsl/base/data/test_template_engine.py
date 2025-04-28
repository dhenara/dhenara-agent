# ruff: noqa: S101
from unittest.mock import MagicMock, patch

from dhenara.agent.dsl.base.data.template_engine import TemplateEngine

# TODO: Tests are broken


class TestTemplateEngine:
    """Test cases for the TemplateEngine class."""

    def test_render_template_simple_var_substitution(self):
        """Test basic variable substitution with $var{}."""
        template = "Hello $var{name}!"
        variables = {"name": "World"}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Hello World!"

    def test_render_template_missing_var(self):
        """Test behavior when variable is missing."""
        template = "Hello $var{name}!"
        variables = {}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Hello $var{name}!"  # Variable not replaced if not found

    def test_render_template_escape_sequences(self):
        """Test escape sequences for template syntax."""
        template = "Template syntax: $$var{name}, $$expr{expression}, $$hier{path}"
        variables = {}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Template syntax: $var{name}, $expr{expression}, $hier{path}"

    def test_render_template_expression_mode(self):
        """Test expression evaluation."""
        template = "Count: $expr{data.count}"
        variables = {"data": {"count": 42}}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Count: 42"

    def test_render_template_complex_expression(self):
        """Test complex expression with operators."""
        template = "Status: $expr{online || 'offline'}"
        variables = {"online": None}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Status: offline"

        template = "Status: $expr{online || 'offline'}"
        variables = {"online": "connected"}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Status: connected"

    def test_render_template_standard_mode(self):
        """Test standard mode (no expression evaluation)."""
        template = "Count: $expr{data.count}"
        variables = {"data": {"count": 42}}
        result = TemplateEngine.render_template(template, variables, mode="standard")
        assert result == "Count: $expr{data.count}"  # Expression not evaluated in standard mode

    def test_render_template_max_words(self):
        """Test word limit functionality."""
        template = "This is a test with multiple words"
        variables = {}
        result = TemplateEngine.render_template(template, variables, max_words=3)
        assert result == "This is a"

    def test_render_template_comparison_operators(self):
        """Test comparison operators in expressions."""
        template = "Greater: $expr{x > y}"
        variables = {"x": 10, "y": 5}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Greater: True"

        template = "Equal: $expr{x == y}"
        variables = {"x": 5, "y": 5}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Equal: True"

    def test_render_template_logical_operators(self):
        """Test logical operators in expressions."""
        template = "Logic: $expr{x && y}"
        variables = {"x": True, "y": False}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Logic: False"

    def test_render_template_array_indexing(self):
        """Test array/list indexing in expressions."""
        template = "Item: $expr{items[0]}"
        variables = {"items": ["apple", "banana", "cherry"]}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Item: apple"

    def test_render_template_python_expression(self):
        """Test Python expression evaluation."""
        template = "Average: $expr{py: sum(scores) / len(scores) if scores else 0}"
        variables = {"scores": [85, 90, 95]}
        result = TemplateEngine.render_template(template, variables)
        assert result == "Average: 90.0"

    def test_evaluate_template(self):
        """Test evaluate_template method preserves type."""
        expr = "$expr{data.numbers}"
        variables = {"data": {"numbers": [1, 2, 3]}}
        result = TemplateEngine.evaluate_template(expr, variables)
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    @patch("dhenara.agent.dsl.base.data.template_engine.logger")
    def test_template_with_error(self, mock_logger):
        """Test error handling in expressions."""
        template = "Result: $expr{a / 0}"
        variables = {"a": 10}
        result = TemplateEngine.render_template(template, variables)
        assert result.startswith("Error:")
        mock_logger.error.assert_called()

    def test_hierarchical_access(self):
        """Test hierarchical access with $hier{}."""
        template = "Task: $expr{$hier{planner.plan_generator}.structured.task_name}"
        variables = {}

        # Create mock execution context
        mock_context = MagicMock()
        mock_context.run_context.execution_context_registry.enable_caching = True

        # Create mock lookup result
        mock_context.run_context.execution_context_registry.lookup_context_by_partial_path.return_value = (
            "planner.plan_generator",
            MagicMock(),
        )

        # Set mock execution result
        mock_context.run_context.execution_context_registry.lookup_context_by_partial_path.return_value[
            1
        ].execution_results = {"plan_generator": {"structured": {"task_name": "Create project plan"}}}

        result = TemplateEngine.render_template(template, variables, execution_context=mock_context)
        assert result == "Task: Create project plan"

    def test_process_escape_sequences(self):
        """Test _process_escape_sequences method."""
        template = "$$expr{test} $$var{name} $$hier{path}"
        result = TemplateEngine._process_escape_sequences(template)
        assert result == "$expr{test} $var{name} $hier{path}"

    def test_process_var_substitutions(self):
        """Test _process_var_substitutions method."""
        template = "Hello $var{name}, your score is $var{score}!"
        variables = {"name": "John", "score": 95}
        result = TemplateEngine._process_var_substitutions(template, variables)
        assert result == "Hello John, your score is 95!"

    def test_try_parse_literal(self):
        """Test _try_parse_literal method."""
        assert TemplateEngine._try_parse_literal("42") == 42
        assert TemplateEngine._try_parse_literal("3.14") == 3.14
        assert TemplateEngine._try_parse_literal("true") is True
        assert TemplateEngine._try_parse_literal("false") is False
        assert TemplateEngine._try_parse_literal("null") is None
        assert TemplateEngine._try_parse_literal("'hello'") == "hello"
        assert TemplateEngine._try_parse_literal('"world"') == "world"
        assert TemplateEngine._try_parse_literal("not_a_literal") is None

    def test_access_property(self):
        """Test _access_property method."""
        # Dictionary access
        obj = {"name": "John"}
        assert TemplateEngine._access_property(obj, "name") == "John"

        # Attribute access
        class TestObj:
            def __init__(self):
                self.name = "Jane"

        test_obj = TestObj()
        assert TemplateEngine._access_property(test_obj, "name") == "Jane"

        # Not found
        assert TemplateEngine._access_property({}, "missing") is None
        assert TemplateEngine._access_property(None, "anything") is None

    def test_empty_template(self):
        """Test behavior with empty template."""
        assert TemplateEngine.render_template("", {}) == ""
        assert TemplateEngine.evaluate_template("", {}) == ""
