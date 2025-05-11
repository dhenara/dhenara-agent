from typing import Any

from pydantic import Field

from dhenara.agent.dsl.base import NodeInput

from .settings import AIModelNodeSettings


class AIModelNodeInput(NodeInput):
    settings_override: AIModelNodeSettings | None = Field(
        default=None,
        description="Optional settings override",
    )
    prompt_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Variables for template resolution in prompt",
        example={"style": "modern", "name": "Annie"},
    )
    # instruction_variables: dict[str, Any] = Field(
    #    default_factory=dict,
    #    description="Variables for template resolution in system instructions",
    #    example={"style": "modern", "name": "Annie"},
    # )
