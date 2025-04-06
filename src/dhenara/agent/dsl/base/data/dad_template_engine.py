import logging
from typing import Any, Literal, TypeVar

from dhenara.agent.types.data import RunEnvParams
from dhenara.ai.types.genai.dhenara.request.data import ObjectTemplate, Prompt, PromptText, TextTemplate

from .template_engine import TemplateEngine

T = TypeVar("T")
logger = logging.getLogger(__name__)


class DADTemplateEngine(TemplateEngine):
    """
    Template engine specialized for Dhenara Agent DSL (DAD), extending the base TemplateEngine.

    This engine provides additional context from RunEnvParams and node execution results
    to be used in template substitution.

    Use `.` notation to access data of input,output& outcome

    Examples:

        CommandNodeSettings:
            commands=[
                "ls -la ${run_dir}",
                "mkdir ${run_dir}/${node_id}/temp_dir",
                "ls -la ${run_dir}",
                "mv ${run_dir}/list_files/temp_dir ${run_dir}/${node_id}/.",
            ]
            working_dir="${run_dir}"


        FolderAnalyzerSettings:
            path="${run_dir}"


        AIModelNodeSettings:
            prompt=Prompt.with_dad_text(
                text="Summarize in plane text under {number_of_chars} characters. ${ai_model_call_1.outcome.text}",
                variables={
                    "number_of_chars": {
                        "default": 60,
                        "allowed": range(50, 100),
                    },
                },
            ),
    """

    @classmethod
    def get_dad_template_keywords_static_vars(cls, run_env_params: RunEnvParams) -> dict:
        # Guaranteed vars
        variables = {
            # --- Externally exposed vars
            #    1.environment variables
            "run_id": run_env_params.run_id,
            "run_dir": str(run_env_params.run_dir),
            "run_root": str(run_env_params.run_root),
            # --- Internal vars
            #    1. state variables
            "_dad_trace_dir": str(run_env_params.trace_dir),
        }

        # Optional vars
        if run_env_params.outcome_repo_dir:
            variables["outcome_repo_dir"] = str(run_env_params.outcome_repo_dir)

        return variables

    @classmethod
    def get_dad_template_keywords_dynamic_vars(
        cls,
        dad_dynamic_variables: dict,
        # Keep adding this list
    ) -> dict:
        """
        Function to cross check only allowed variables are processed as dad_dynamic_variables
        """
        variables = {}

        # Check and add
        if "node_id" in dad_dynamic_variables.keys() and dad_dynamic_variables["node_id"]:
            variables["node_id"] = str(dad_dynamic_variables["node_id"])

        if "node_hier" in dad_dynamic_variables.keys() and dad_dynamic_variables["node_hier"]:
            variables["node_hier"] = str(dad_dynamic_variables["node_hier"])

        return variables

    @classmethod
    def render_dad_template(
        cls,
        template: str | Prompt | TextTemplate | ObjectTemplate,
        variables: dict[str, Any],
        dad_dynamic_variables: dict[str, Any],
        run_env_params: RunEnvParams,
        node_execution_results: dict[str, Any],
        mode: Literal["standard", "expression"] = "expression",
        max_words: int | None = None,
        max_words_file: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Render a template with DAD-specific context.

        Args:
            template: String, Prompt, TextTemplate, or ObjectTemplate to render
            variables: User-provided variables for template rendering
            dad_dynamic_variables: Dynamic variables from the DAD context
            run_env_params: Run environment parameters
            node_execution_results: Results from previous node executions
            mode: "standard" for basic substitution, "expression" for advanced evaluation
            **kwargs: Additional variables for template formatting

        Returns:
            Rendered template (string for TextTemplate, raw value for ObjectTemplate)
        """
        if not template:
            return ""

        # Combine all variables with precedence: kwargs > variables > node_results > run_env
        combined_variables = {}

        # Add node execution results
        if node_execution_results:
            combined_variables.update(node_execution_results)

        # Add user-provided variables (overriding previous)
        if variables:
            combined_variables.update(variables)

        # Add kwargs (highest precedence)
        if kwargs:
            combined_variables.update(kwargs)

        # Add DAD variables
        combined_variables.update(cls.get_dad_template_keywords_static_vars(run_env_params))
        combined_variables.update(cls.get_dad_template_keywords_dynamic_vars(dad_dynamic_variables))

        try:
            # Handle string templates
            if isinstance(template, str):
                rendered_text = cls.render_template(template, combined_variables, mode)
                return cls._apply_word_limit(rendered_text, max_words)

            # Handle Prompt objects
            elif isinstance(template, Prompt):
                combined_variables.update(template.variables)

                if isinstance(template.text, PromptText):
                    return cls._process_prompt_text(
                        prompt_text=template.text,
                        variables=combined_variables,
                        mode=mode,
                        max_words=max_words,
                    )
                elif isinstance(template.text, str):
                    rendered_text = cls.render_template(template.text, combined_variables, mode)
                    return cls._apply_word_limit(rendered_text, max_words)
                else:
                    raise ValueError(f"Unsupported prompt.text type: {type(template.text)}")

            elif isinstance(template, TextTemplate):
                return cls._process_text_template(
                    text_template=template,
                    variables=combined_variables,
                    mode=mode,
                    max_words=max_words,
                )

            # Handle ObjectTemplate - preserves type
            elif isinstance(template, ObjectTemplate):
                return cls.evaluate_single_expression(template.expression, combined_variables)

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
        mode: Literal["standard", "expression"],
        max_words: int | None,
    ) -> str:
        """Process a PromptText object."""
        if prompt_text.content:
            template_text = prompt_text.content.get_content()
            parsed_text = cls.render_template(template_text, variables, mode)
            return cls._apply_word_limit(parsed_text, max_words)
        else:
            # If no content, use the template text directly
            return cls._process_text_template(
                text_template=prompt_text.template,
                variables=variables,
                mode=mode,
                max_words=max_words,
            )

    @classmethod
    def _process_text_template(
        cls,
        text_template: TextTemplate,
        variables: dict[str, Any],
        mode: Literal["standard", "expression"],
        max_words: int | None,
    ) -> str:
        """Process a PromptText object."""

        # Phase 1: Extract and protect DAD template variables (${...})
        import re

        protected_dad_vars = {}

        # Find and replace DAD template variables with placeholders
        def replace_dad_vars(match):
            dad_var = match.group(0)  # Get the full ${...} variable
            # Create a unique placeholder that won't conflict with any text
            placeholder = f"__DAD_VAR_{len(protected_dad_vars)}__"
            protected_dad_vars[placeholder] = dad_var
            return placeholder

        # Pattern to find DAD template variables
        dad_var_pattern = r"\${[^}]+}"

        # Replace all ${...} with placeholders
        protected_text = re.sub(dad_var_pattern, replace_dad_vars, text_template.text)

        # Phase 2: Now safely apply Python string formatting
        # This will format {var} style variables without interfering with DAD variables
        _temp = text_template.model_copy()
        _temp.text = protected_text
        _temp.disable_checks = False  # Not needed since DAD vars are now placeholders
        formatted_text = _temp.format(**variables)

        # Phase 3: Restore DAD template variables for later processing
        for placeholder, dad_var in protected_dad_vars.items():
            formatted_text = formatted_text.replace(placeholder, dad_var)

        # Phase 4: Now process the DAD template variables
        parsed_text = cls.render_template(formatted_text, variables, mode)

        return cls._apply_word_limit(parsed_text, max_words)

    @staticmethod
    def _apply_word_limit(text: str, max_words: int | None) -> str:
        """Apply word limit to text if specified."""
        if max_words and text:
            words = text.split()
            return " ".join(words[:max_words])
        return text
