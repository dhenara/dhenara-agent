from pydantic import BaseModel, Field

from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    EventType,
    Flow,
    NodeRecordSettings,
    SpecialNodeIDEnum,
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


# Define structured output models
class CodeFile(BaseModel):
    filename: str = Field(..., description="Name of the file")
    content: str = Field(..., description="Content of the file")
    language: str = Field(..., description="Programming language")


class CodePlan(BaseModel):
    description: str = Field(..., description="Description of the code plan")
    files: list[CodeFile] = Field(..., description="Files to generate")
    dependencies: list[str] = Field(default_factory=list, description="Dependencies")


test_mode = False

# Define a flow
flow = (
    Flow()
    # First node: Create a code plan
    .node(
        "ai_model_call_1",
        AIModelNode(
            resources=[
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={
                        ResourceQueryFieldsEnum.model_name: "gpt-4o-mini",
                        ResourceQueryFieldsEnum.api_provider: AIModelAPIProviderEnum.OPEN_AI,
                    },
                ),
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "claude-3-7-sonnet"},
                    is_default=True,
                ),
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "gemini-2.0-flashl-lite"},
                ),
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "o3-mini"},
                ),
            ],
            pre_events=[EventType.node_input_required],
            node_settings=AIModelNodeSettings(
                system_instructions=[
                    "You are an AI assistant in a general purpose chatbot",
                    "Always respond in markdown format.",
                ],
                prompt=Prompt(
                    role=PromptMessageRoleEnum.USER,
                    text=PromptText(
                        content=None,
                        template=TextTemplate(
                            text="{user_query}",
                            variables={"user_query": {}},
                        ),
                    ),
                ),
                model_call_config=AIModelCallConfig(
                    # structured_output=CodePlan,
                    test_mode=test_mode,
                ),
            ),
            record_settings=NodeRecordSettings.with_outcome_format("text"),  # Enforce test as default is json
            git_settings=None,
        ),
    )
    .node(
        "title_generator",
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
                system_instructions=[
                    "You are a summarizer which generate a title text under 60 characters from the prompts.",
                ],
                prompt=Prompt(
                    role=PromptMessageRoleEnum.USER,
                    text=PromptText(
                        content=None,
                        template=TextTemplate(
                            text="Summarize in plane text under {number_of_chars} characters.",
                            variables={
                                "number_of_chars": {
                                    "default": 60,
                                    "allowed": range(50, 100),
                                }
                            },
                        ),
                    ),
                ),
                context_sources=[SpecialNodeIDEnum.PREVIOUS],
                model_call_config=AIModelCallConfig(
                    # structured_output=CodePlan,
                    test_mode=test_mode,
                ),
            ),
            record_settings=NodeRecordSettings.with_outcome_format("text"),  # Enforce test as default is json
            git_settings=None,
        ),
    )
)
