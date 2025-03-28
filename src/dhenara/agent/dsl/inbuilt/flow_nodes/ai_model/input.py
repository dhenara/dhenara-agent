from typing import Any

from pydantic import Field

from dhenara.agent.dsl.base import NodeInput
from dhenara.ai.types import ResourceConfigItem

from .settings import AIModelNodeSettings


class AIModelNodeInput(NodeInput):
    prompt_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Variables for template resolution in prompt",
        example={"style": "modern", "name": "Annie"},
    )
    instruction_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Variables for template resolution in system instructions",
        example={"style": "modern", "name": "Annie"},
    )
    settings_override: AIModelNodeSettings | None = Field(
        default=None,
        description="Optional settings override",
    )
    resources_override: list[ResourceConfigItem] = Field(
        default_factory=list,
        description="List of resources to be used",
    )
