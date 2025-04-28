# ruff: noqa: S101
from unittest.mock import MagicMock, patch

from dhenara.agent.dsl.base.data.dad_template_engine import DADTemplateEngine
from dhenara.ai.types.genai.dhenara.request.data import (
    Content,
    ContentType,
    ObjectTemplate,
    Prompt,
    PromptMessageRoleEnum,
    PromptText,
    TextTemplate,
)


class TestDADTemplateEngine:
    """Test cases for the DADTemplateEngine class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock execution context
        self.mock_context = MagicMock()

        # Set up static variables
        self.mock_context.run_context.get_dad_template_static_variables.return_value = {
            "run_dir": "/tmp/test",
            "run_id": "test_run_123",
        }

        # Set up dynamic variables
        self.mock_context.get_dad_template_dynamic_variables.return_value = {
            "node_id": "test_node",
            "component_id": "test_component",
        }

    def test_render_dad_template_string(self):
        """Test rendering a string template."""
        template = "Running in $var{run_dir} with node $var{node_id}"
        result = DADTemplateEngine.render_dad_template(template, {}, self.mock_context)
        assert result == "Running in /tmp/test with node test_node"

    def test_render_dad_template_with_user_variables(self):
        """Test rendering with user-provided variables."""
        template = "$var{custom_var} in $var{run_dir}"
        result = DADTemplateEngine.render_dad_template(template, {"custom_var": "My variable"}, self.mock_context)
        assert result == "My variable in /tmp/test"

    def test_render_dad_template_with_kwargs(self):
        """Test rendering with additional kwargs."""
        template = "$var{custom_var} in $var{run_dir} with $var{extra_param}"
        result = DADTemplateEngine.render_dad_template(
            template, {"custom_var": "My variable"}, self.mock_context, extra_param="extra value"
        )
        assert result == "My variable in /tmp/test with extra value"

    def test_render_dad_template_object_template(self):
        """Test rendering an ObjectTemplate."""
        obj_template = ObjectTemplate(expression="$expr{data.value}")

        with patch("dhenara.agent.dsl.base.data.dad_template_engine.TemplateEngine.evaluate_template") as mock_evaluate:
            mock_evaluate.return_value = 42

            result = DADTemplateEngine.render_dad_template(obj_template, {"data": {"value": 42}}, self.mock_context)

            assert result == 42
            mock_evaluate.assert_called_once()

    def test_render_dad_template_prompt(self):
        """Test rendering a Prompt object with string text."""
        prompt = Prompt.with_dad_text(text="Template with $var{run_id}", variables={})

        result = DADTemplateEngine.render_dad_template(prompt, {}, self.mock_context)

        assert result == "Template with test_run_123"

    def test_render_dad_template_prompt_with_prompt_text(self):
        """Test rendering a Prompt object with PromptText."""
        prompt_text = PromptText(
            content=None,
            template=TextTemplate(
                text="Template with $var{run_id} and $var{custom_var}",
                variables={"custom_var": {"default": "default value"}},
            ),
        )

        prompt = Prompt(text=prompt_text, variables={}, role=PromptMessageRoleEnum.USER)

        result = DADTemplateEngine.render_dad_template(prompt, {}, self.mock_context)

        assert result == "Template with test_run_123 and default value"

    def test_render_dad_template_text_template(self):
        """Test rendering a TextTemplate."""
        text_template = TextTemplate(
            text="Template with $var{run_id} and $var{custom_var}",
            variables={"custom_var": {"default": "default value"}},
        )

        result = DADTemplateEngine.render_dad_template(text_template, {}, self.mock_context)

        assert result == "Template with test_run_123 and default value"

    def test_render_dad_template_text_template_override_default(self):
        """Test rendering a TextTemplate with overridden default values."""
        text_template = TextTemplate(
            text="Template with $var{run_id} and $var{custom_var}",
            variables={"custom_var": {"default": "default value"}},
        )

        result = DADTemplateEngine.render_dad_template(text_template, {"custom_var": "custom value"}, self.mock_context)

        assert result == "Template with test_run_123 and custom value"

    @patch("dhenara.agent.dsl.base.data.dad_template_engine.logger")
    def test_render_dad_template_text_template_missing_variables(self, mock_logger):
        """Test handling missing variables in TextTemplate."""
        text_template = TextTemplate(
            text="Template with $var{run_id} and $var{missing_var}",
            variables={"missing_var": {}},  # No default value
        )

        result = DADTemplateEngine.render_dad_template(text_template, {}, self.mock_context)

        assert result == "Template with test_run_123 and $var{missing_var}"
        mock_logger.error.assert_called_once()

    def test_render_dad_template_prompt_text_with_content(self):
        """Test rendering PromptText with content."""
        # prompt_text = PromptText(content=MagicMock(), template=TextTemplate(text="Not used", variables={}))
        # prompt_text.content.get_content.return_value = "Content with $var{run_id}"
        prompt_text = PromptText(
            content=Content(type=ContentType.TEXT, text="Content with $var{run_id}"),
        )

        result = DADTemplateEngine._process_prompt_text(
            prompt_text, {"run_id": "test_run_123"}, self.mock_context, mode="expression", max_words=None
        )

        assert result == "Content with test_run_123"

    def test_apply_word_limit(self):
        """Test _apply_word_limit method."""
        text = "This is a test with multiple words"

        result = DADTemplateEngine._apply_word_limit(text, 3)
        assert result == "This is a"

        result = DADTemplateEngine._apply_word_limit(text, None)
        assert result == text

    @patch("dhenara.agent.dsl.base.data.dad_template_engine.logger")
    def test_render_dad_template_error_handling(self, mock_logger):
        """Test error handling in render_dad_template."""
        # Create a template that will cause an error
        with patch(
            "dhenara.agent.dsl.base.data.dad_template_engine.TemplateEngine.render_template",
            side_effect=Exception("Test error"),
        ):
            result = DADTemplateEngine.render_dad_template("Template $var{run_id}", {}, self.mock_context)

            assert result.startswith("Error rendering template:")
            mock_logger.error.assert_called_once()

    def test_render_dad_template_none(self):
        """Test handling None template."""
        result = DADTemplateEngine.render_dad_template(None, {}, self.mock_context)
        assert result is None

    def test_render_dad_template_unsupported_type(self):
        """Test handling unsupported template type."""
        # with pytest.raises(ValueError) as excinfo:
        #    DADTemplateEngine.render_dad_template(123, {}, self.mock_context)

        # assert "Unsupported template type" in str(excinfo.value)

        result = DADTemplateEngine.render_dad_template(123, {}, self.mock_context)

        assert isinstance(result, str)
        assert "Error rendering template" in result
        assert "Unsupported template type" in result
