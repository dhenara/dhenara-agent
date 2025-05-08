import logging
from typing import TYPE_CHECKING, Any, Literal, Optional, TypeVar

from dhenara.ai.types.genai.dhenara.request.data import ObjectTemplate, Prompt, PromptText, TextTemplate

from .template_engine import TemplateEngine

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from dhenara.agent.dsl.base import ExecutionContext
else:
    ExecutionContext = Any

T = TypeVar("T")
logger = logging.getLogger(__name__)


class DADTemplateEngine(TemplateEngine):
    """
    Template engine specialized for Dhenara Agent DSL (DAD), extending the base TemplateEngine.

    This engine provides additional context from RunEnvParams and node execution results
    to be used in template substitution, with support for hierarchical node resolution.

    Use `.` notation to access data from node results:
    - $var{} for simple variable substitution
    - $expr{} for complex expressions with property access, operators, etc.

    Examples:

        CommandNodeSettings:
            commands=[
                "ls -la $expr{run_dir}",
                "mkdir $expr{run_dir}/$expr{node_id}/temp_dir",
                "ls -la $expr{run_dir}",
                "mv $expr{run_dir}/list_files/temp_dir $expr{run_dir/node_id}/.",
            ]
            working_dir="$expr{run_dir}"


        FolderAnalyzerSettings:
            path="$expr{run_dir}"


        AIModelNodeSettings:
            prompt=Prompt.with_dad_text(
                text="Summarize in plane text under $var{number_of_chars} chars. $expr{ai_model_call_1.outcome.text}",
                variables={
                    "number_of_chars": {
                        "default": 60,
                        "allowed": range(50, 100),
                    },
                },
            ),
    """

    @classmethod
    def render_dad_template(
        cls,
        template: str | Prompt | TextTemplate | ObjectTemplate,
        variables: dict[str, Any],
        execution_context: ExecutionContext,
        mode: Literal["standard", "expression"] = "expression",
        max_words: int | None = None,
        max_words_file: int | None = None,
        debug_mode: bool = False,  # To selectively enable debug for certain calls manually
        **kwargs: Any,
    ) -> Any:
        """
        Render a template with DAD-specific context and hierarchical node resolution.

        Args:
            template: Template to render (string, Prompt, TextTemplate, or ObjectTemplate)
            variables: User-provided variables for template rendering
            execution_context: Current execution context for hierarchical node lookup
            mode: "standard" for basic substitution, "expression" for advanced evaluation
            max_words: Maximum number of words to include in text output
            max_words_file: Maximum number of words for file content (unused, for API compatibility)
            **kwargs: Additional variables for template formatting

        Returns:
            Rendered template (preserves type for ObjectTemplate, returns string for others)
        """
        if template is None:
            return None

        combined_variables = {}

        # Add user-provided variables (overriding previous)
        if variables:
            combined_variables.update(variables)

        # Add kwargs (highest precedence)
        if kwargs:
            combined_variables.update(kwargs)

        # Add DAD variables
        # NOTE: Below are the set of variables available via $var{} replacements
        dad_static_variables = execution_context.run_context.get_dad_template_static_variables()
        dad_dynamic_variables = execution_context.get_dad_template_dynamic_variables()
        component_variables = execution_context.get_component_variables()
        control_block_immediate_parent_variables = execution_context.get_control_block_immediate_parent_variables()
        control_block_hier_parent_variables = execution_context.get_control_block_hierarchical_parent_variables()

        combined_variables.update(dad_static_variables)
        combined_variables.update(dad_dynamic_variables)
        combined_variables.update(control_block_hier_parent_variables)
        combined_variables.update(control_block_immediate_parent_variables)
        combined_variables.update(component_variables)

        if debug_mode:
            logger.debug(f"dad_template: template = {template} combined_variables: {combined_variables}")

        try:
            # Handle ObjectTemplate - preserves type
            if isinstance(template, ObjectTemplate):
                return cls.evaluate_template(template.expression, combined_variables, execution_context)

            # Handle string templates
            elif isinstance(template, str):
                rendered_text = cls.render_template(
                    template=template,
                    variables=combined_variables,
                    execution_context=execution_context,
                    mode=mode,
                    debug_mode=debug_mode,
                )
                return cls._apply_word_limit(rendered_text, max_words)

            # Handle Prompt objects
            elif isinstance(template, Prompt):
                combined_variables.update(template.variables)

                if isinstance(template.text, PromptText):
                    return cls._process_prompt_text(
                        prompt_text=template.text,
                        variables=combined_variables,
                        execution_context=execution_context,
                        mode=mode,
                        max_words=max_words,
                        debug_mode=debug_mode,
                    )
                elif isinstance(template.text, str):
                    rendered_text = cls.render_template(
                        template=template.text,
                        variables=combined_variables,
                        execution_context=execution_context,
                        mode=mode,
                        debug_mode=debug_mode,
                    )
                    return cls._apply_word_limit(rendered_text, max_words)
                else:
                    raise ValueError(f"Unsupported prompt.text type: {type(template.text)}")

            elif isinstance(template, TextTemplate):
                return cls._process_text_template(
                    text_template=template,
                    variables=combined_variables,
                    execution_context=execution_context,
                    mode=mode,
                    max_words=max_words,
                    debug_mode=debug_mode,
                )

            else:
                raise ValueError(f"Unsupported template type: {type(template)}")

        except Exception as e:
            logger.error(f"Error rendering DAD template: {e}", exc_info=True)
            return f"Error rendering template: {e!s}"

    @classmethod
    def _process_prompt_text(
        cls,
        prompt_text: PromptText,
        variables: dict[str, Any],
        execution_context: Optional["ExecutionContext"],
        mode: Literal["standard", "expression"],
        max_words: int | None,
        debug_mode: bool = False,
    ) -> str:
        """Process a PromptText object."""
        if prompt_text.content:
            template_text = prompt_text.content.get_content()
            parsed_text = cls.render_template(
                template=template_text,
                variables=variables,
                execution_context=execution_context,
                mode=mode,
                debug_mode=debug_mode,
            )
            return cls._apply_word_limit(parsed_text, max_words)
        else:
            # If no content, use the template text directly
            return cls._process_text_template(
                text_template=prompt_text.template,
                variables=variables,
                execution_context=execution_context,
                mode=mode,
                max_words=max_words,
                debug_mode=debug_mode,
            )

    @classmethod
    def _process_text_template(
        cls,
        text_template: TextTemplate,
        variables: dict[str, Any],
        execution_context: Optional["ExecutionContext"],
        mode: Literal["standard", "expression"],
        max_words: int | None,
        debug_mode: bool = False,
    ) -> str:
        # Add variables diefault values, if missing in the incoming variables
        variables_defaults = text_template.get_args_default_values()
        missing_variables_with_defaults = {
            key: value for key, value in variables_defaults.items() if key not in variables.keys()
        }

        variables.update(missing_variables_with_defaults)

        # Do a final check if still some variable are missing
        missing_variable_names = [var for var in text_template.get_variable_names() if var not in variables.keys()]
        if missing_variable_names:
            logger.error(
                "Some variabes in the TextTemplate were not provided with any values. "
                "This could lead to unexpected behaviours. "
                f"Misssing variables are {missing_variable_names}"
            )

        parsed_text = cls.render_template(
            template=text_template.text,
            variables=variables,
            execution_context=execution_context,
            mode=mode,
            debug_mode=debug_mode,
        )
        return cls._apply_word_limit(parsed_text, max_words)

    @staticmethod
    def _apply_word_limit(text: str, max_words: int | None) -> str:
        """Apply word limit to text if specified."""
        if max_words and text:
            words = text.split()
            return " ".join(words[:max_words])
        return text
