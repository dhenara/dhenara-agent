# dhenara/agent/nodes/base.py
import json
import re
from typing import Any

from pydantic import Field, field_validator, model_validator

from dhenara.agent.dsl.flow import FlowExecutionContext, FlowNodeDefinition
from dhenara.agent.engine.handler.handlers.ai_model_call import AIModelCallHandler
from dhenara.agent.types.flow import (
    AISettings,
    FlowNodeInput,
    FlowNodeTypeEnum,
    NodeInputSettings,
)
from dhenara.ai.types import ResourceConfigItem
from dhenara.ai.types.shared.base import BaseModel


# dhenara/agent/nodes/ai_model.py
class AIModelOutput(BaseModel):
    """Base model for AI model outputs."""

    # TODO: This should match with dhenara.ai package output
    raw_text: str


class AIModelCall(FlowNodeDefinition):
    resources: list[ResourceConfigItem] = Field(
        default_factory=list,
        description="List of resources to be used",
    )
    tools: list = Field(
        default_factory=list,
        description="Tools",
    )
    ai_settings: AISettings | None = Field(
        default=None,
        description="Node specific AP API settings/ options ",
    )
    input_settings: NodeInputSettings | None = Field(
        default=None,
        description="Input Settings",
    )  # TODO: Consider removing this field and take care of previous context seperately

    @field_validator("resources")
    @classmethod
    def validate_node_resources(
        cls,
        v: list[ResourceConfigItem],
    ) -> list[ResourceConfigItem]:
        """Validate that node IDs are unique within the same flow level."""
        # Ignore empty lists
        if not v:
            return v

        default_count = sum(1 for resource in v if resource.is_default)
        if default_count > 1:
            raise ValueError("Only one resource can be set as default")

        # If there is only one resource, set it as default and return
        if len(v) == 1:
            v[0].is_default = True
            return v
        else:
            if default_count < 1:
                raise ValueError("resources: One resource should be set as default")
            return v

    @model_validator(mode="after")
    def validate_node_type_settings(self):
        if not (self.ai_settings or self.input_settings):
            raise ValueError("ai_settings or input_settings is required for AIModelCall")

        return self

    # @model_validator(mode="after")
    # def validate_input_settings(self) -> "FlowNode":
    #    """Validates that input settings and AI settings are not conflicting.
    #
    #    This validator ensures that user input sources and node prompts are not
    #    configured simultaneously, which would create ambiguous input handling.
    #
    #    Returns:
    #        Self instance if validation passes
    #    Raises:
    #        ValueError: If conflicting settings are detected
    #    """
    #    has_prompt = self.ai_settings and self.ai_settings.node_prompt.format() and self.ai_settings.node_prompt.prompt
    #    has_user_input = self.input_settings and self.input_settings.input_source and self.input_settings.input_source.user_input_sources  # noqa: E501, W505
    #    if has_prompt and has_user_input:
    #        raise ValueError(
    #            "Illegal input settings configuration: "
    #            "`input_source.user_input_sources` and `ai_settings.node_prompt.prompt` "
    #            "cannot be set simultaneously. To modify user inputs for this node, "
    #            "use the `pre` and `post` fields of `node_prompt`, not the `prompt` field.",
    #        )
    #    return self

    async def get_full_input_content(self, node_input: FlowNodeInput, **kwargs) -> str:
        node_prompt = self.ai_settings.node_prompt if self.ai_settings and self.ai_settings.node_prompt else None
        input_content = node_input.content.get_content() if node_input and node_input.content else None

        if node_prompt:
            if input_content is None:
                input_content = ""  # An empty string is better that the word None

            kwargs.update({"dh_input_content": input_content})

            return node_prompt.format(**kwargs)

        else:
            if not input_content:
                raise ValueError(
                    f"Illegal Node setting for node {self.identifier}:  node_prompt and input_content are empty"
                )

            return input_content

    def is_streaming(self):
        return self.type in [FlowNodeTypeEnum.ai_model_call_stream]

    def check_resource_in_node(self, resource: ResourceConfigItem) -> bool:
        """
        Checks if a given resource exists in the node's resource list.

        Args:
            resource: ResourceConfigItem object to check for

        Returns:
            bool: True if the resource exists in the node's resources, False otherwise
        """
        if not self.resources:
            return False

        return any(existing_resource.is_same_as(resource) for existing_resource in self.resources)

    async def execute(self, context: "FlowExecutionContext") -> AIModelOutput:
        """Execute an AI model call."""
        handler = AIModelCallHandler()
        return await handler.handle(
            flow_node=self,
            flow_context=context,
            resource_config=context.resource_config,
        )


# TODO: Integrate structured output into legacy handlers
class TODOAIModelCall(FlowNodeDefinition):
    """Definition for an AI model call node."""

    def __init__(
        self,
        model_name: str,
        prompt_template: str,
        system_instructions: list[str] | None = None,
        options: dict[str, Any] | None = None,
        # outcome_settings: Optional[OutcomeSettings] = None,
    ):
        # super().__init__(outcome_settings=outcome_settings)
        self.model_name = model_name
        self.prompt_template = prompt_template
        self.system_instructions = system_instructions or []
        self.options = options or {}
        # self.structured_output = structured_output

    async def execute(self, context: "FlowExecutionContext") -> AIModelOutput:
        """Execute an AI model call."""
        # Resolve the prompt template
        prompt = context.evaluate_template(self.prompt_template)

        # Add structured output schema if needed
        if self.structured_output:
            schema = self.structured_output.model_json_schema()
            schema_text = json.dumps(schema, indent=2)
            prompt += f"\n\nRespond with JSON matching this schema:\n```json\n{schema_text}\n```"

        # Get an AI model client
        model = context.get_model(self.model_name)

        # Execute the call
        response = await model.generate(
            prompt=prompt,
            system_instructions=self.system_instructions,
            options=self.options,
        )

        # Parse structured output if requested
        result = AIModelOutput(raw_text=response.text)
        if self.structured_output:
            try:
                # Extract and parse JSON
                json_text = self._extract_json(response.text)
                structured = self.structured_output.model_validate(json.loads(json_text))
                result.structured = structured
            except Exception as e:
                context.logger.warning(f"Failed to parse structured output: {e}")

        # Record outcome if configured
        if self.outcome_settings:
            await context.record_outcome(self, result)

        return result

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text."""
        # First try to extract JSON blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_match:
            return json_match.group(1)

        # If that fails, try to find JSON objects
        json_pattern = r"(\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\})"
        matches = re.findall(json_pattern, text)
        if matches:
            return max(matches, key=len)

        # If all else fails, return the text as-is
        return text
