from pydantic import BaseModel, Field

from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    Flow,
    NodeRecordSettings,
    RecordSettingsItem,
)
from dhenara.ai.types import (
    AIModelAPIProviderEnum,
    AIModelCallConfig,
    Prompt,
    PromptMessageRoleEnum,
    PromptText,
    ResourceConfigItem,
    ResourceConfigItemTypeEnum,
    ResourceQueryFieldsEnum,
    TextTemplate,
)

# NOTE: `agent_identifier` is used for naming run dirs.
# Its OK to change during bringup, but be aware of the run dir naminig dependency
agent_identifier = "abcd"


# Define structured output models
class CodeFile(BaseModel):
    filename: str = Field(..., description="Name of the file")
    content: str = Field(..., description="Content of the file")
    language: str = Field(..., description="Programming language")


class CodePlan(BaseModel):
    description: str = Field(..., description="Description of the code plan")
    files: list[CodeFile] = Field(..., description="Files to generate")
    dependencies: list[str] = Field(default_factory=list, description="Dependencies")


# Define a flow
flow = (
    Flow()
    # First node: Create a code plan
    .node(
        "create_plan",
        AIModelNode(
            resources=[
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={
                        ResourceQueryFieldsEnum.model_name: "gpt-4o-mini",
                        ResourceQueryFieldsEnum.api_provider: AIModelAPIProviderEnum.OPEN_AI,
                    },
                ),
            ],
            node_settings=AIModelNodeSettings(
                system_instructions=None,
                prompt=Prompt(
                    role=PromptMessageRoleEnum.USER,
                    text=PromptText(
                        content=None,
                        template=TextTemplate(
                            text="Create a code plan for: {requested_plan}",
                            variables={"requested_plan": {"default_value": "Flutter project"}},
                        ),
                    ),
                ),
                model_call_config=AIModelCallConfig(
                    structured_output=CodePlan,
                ),
            ),
            record_settings=NodeRecordSettings(
                outcome=RecordSettingsItem(
                    path="plans/",
                    file_format="json",
                    filename="initial_plan.json",
                    git_commit=True,
                    git_commit_message="Inital Plan on run ${run_id}",
                )
            ),
        ),
    )
)
