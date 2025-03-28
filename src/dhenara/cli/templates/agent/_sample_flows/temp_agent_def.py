from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field

from dhenara.agent.dsl import (
    AgentNode,
    AIModelNode,
    AIModelNodeSettings,
    Flow,
    NodeOutcomeSettings,
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
    StructuredOutputConfig,
    TextTemplate,
)

# NOTE: `agent_identifier` is used for naming run dirs.
# Its OK to change during bringup, but be aware of the run dir naminig dependency
agent_identifier = "abcd"


# Define structured output models
class CodeFile(PydanticBaseModel):
    filename: str = Field(..., description="Name of the file")
    content: str = Field(..., description="Content of the file")
    language: str = Field(..., description="Programming language")


class CodePlan(PydanticBaseModel):
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
            settings=AIModelNodeSettings(
                system_instructions=None,
                prompt=Prompt(
                    role=PromptMessageRoleEnum.USER,
                    text=PromptText(
                        content=None,
                        template=TextTemplate(
                            text="Create a code plan for: ${requested_plan}",
                            variables={"requested_plan": {"default_value": "Flutter project"}},
                        ),
                    ),
                ),
                model_call_config=AIModelCallConfig(
                    structured_output=StructuredOutputConfig(output_schema=CodePlan),
                ),
            ),
            outcome_settings=NodeOutcomeSettings(
                path_template="code_generation/${run_id}",
                filename_template="plan.json",
                commit=True,
            ),
        ),
    )
)
"""
# Loop through the files in the plan
for_each_block(
    items="${create_plan.structured.files}",
    item_var="file_info",
    body=Flow().node(
        "generate_file",
        AIModelNode(
            model_name="claude-3-sonnet",
            prompt_template=(
                "Generate code for: ${file_info.filename}\n"
                "Language: ${file_info.language}\n"
                "Purpose: ${file_info.description}"
            ),
            outcome_settings=NodeOutcomeSettings(
                path_template="code_generation/${run_id}/files",
                filename_template="${file_info.filename}",
                content_template="${generate_file.raw_text}",
                commit=True,
                commit_message_template="Generated ${file_info.filename}",
            ),
        ),
    ),
).node(
    "create_readme",
    AIModelNode(
        model_name="claude-3-haiku",
        prompt_template=(
            "Create a README.md for the project.\n"
            "Project description: ${create_plan.structured.description}\n"
            "Files: ${', '.join([f.filename for f in create_plan.structured.files])}\n"
            "Dependencies: ${', '.join(create_plan.structured.dependencies)}"
        ),
        outcome_settings=NodeOutcomeSettings(
            path_template="code_generation/${run_id}",
            filename_template="README.md",
            content_template="${create_readme.raw_text}",
            commit=True,
            commit_message_template="Added README for ${run_id}",
        ),
    ),
)
"""

# Agent definition,  modify as per your need
# NOTE: The instance name should be `agent_definition`
agent_node = AgentNode(
    id=agent_identifier,
    independent=True,
    multi_phase=False,
    description="",
    # system_instructions=["Always respond in markdown format."],
    flow=flow,
)
