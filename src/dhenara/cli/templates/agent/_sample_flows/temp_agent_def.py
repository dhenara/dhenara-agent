from pydantic import BaseModel, Field

from dhenara.agent.dsl import (
    AgentNode,
    AIModelCall,
    Flow,
)
from dhenara.agent.dsl import (
    ExecutableNodeOutcomeSettings as OutcomeSettings,
)
from dhenara.agent.types import (
    AISettings,
    PromptTemplate,
)
from dhenara.ai.types import (
    AIModelAPIProviderEnum,
    ResourceConfigItem,
    ResourceConfigItemTypeEnum,
    ResourceQueryFieldsEnum,
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
        AIModelCall(
            resources=[
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={
                        ResourceQueryFieldsEnum.model_name: "gpt-4o-mini",
                        ResourceQueryFieldsEnum.api_provider: AIModelAPIProviderEnum.OPEN_AI,
                    },
                ),
            ],
            ai_settings=AISettings(
                system_instructions=[],
                node_prompt=PromptTemplate(
                    template="Create a code plan for: ${requested_plan}",
                    # template="tell me a strory",
                    default_values={},
                ),
                structured_output=CodePlan,
                options_overrides=None,
            ),
            outcome_settings=OutcomeSettings(
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
        AIModelCall(
            model_name="claude-3-sonnet",
            prompt_template=(
                "Generate code for: ${file_info.filename}\n"
                "Language: ${file_info.language}\n"
                "Purpose: ${file_info.description}"
            ),
            outcome_settings=OutcomeSettings(
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
    AIModelCall(
        model_name="claude-3-haiku",
        prompt_template=(
            "Create a README.md for the project.\n"
            "Project description: ${create_plan.structured.description}\n"
            "Files: ${', '.join([f.filename for f in create_plan.structured.files])}\n"
            "Dependencies: ${', '.join(create_plan.structured.dependencies)}"
        ),
        outcome_settings=OutcomeSettings(
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
