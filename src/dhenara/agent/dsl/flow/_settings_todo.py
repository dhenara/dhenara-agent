import json
from typing import Literal

from pydantic import Field

from dhenara.agent.type.base import BaseModel


# TODO: Move to AI  model
class StructuredOutputSettings(BaseModel):
    """Settings for structured output from LLM."""

    model_class: type[BaseModel] = Field(
        ...,
        description="The model class for the structured output",
    )
    description: str | None = Field(
        default=None,
        description="Description of the expected output format for the LLM",
    )
    include_schema_in_prompt: bool = Field(
        default=True,
        description="Whether to include the schema in the prompt for the LLM",
    )
    handling_strategy: Literal["strict", "best_effort", "hybrid"] = Field(
        default="hybrid",
        description="How to handle parsing failures",
    )

    def generate_schema_prompt(self) -> str:
        """Generate a prompt describing the expected output format."""
        schema = self.model_class.model_json_schema()

        prompt = (
            f"Return the response as a JSON object with the following structure:"
            f"\n```json\n{json.dumps(schema, indent=2)}\n```\n"
        )
        if self.description:
            prompt = f"{self.description}\n\n{prompt}"

        return prompt
