# ruff:noqa: E501
from pydantic import BaseModel, Field

from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    CommandNode,
    CommandNodeSettings,
    EventType,
    FileOperationNode,
    FileOperationNodeSettings,
    Flow,
    FolderAnalyzerNode,
    FolderAnalyzerSettings,
    NodeRecordSettings,
    ProgressMonitorNode,
    ProgressMonitorNodeSettings,
)
from dhenara.ai.types import (
    AIModelCallConfig,
    Prompt,
    PromptMessageRoleEnum,
    PromptText,
    ResourceConfigItem,
    ResourceConfigItemTypeEnum,
    ResourceQueryFieldsEnum,
    TextTemplate,
)


# Define the structured output models
class FileChange(BaseModel):
    path: str = Field(..., description="Path to the file to be created or modified")
    content: str = Field(..., description="Content of the file")
    description: str = Field(..., description="Description of the changes made to the file")


class CommandToRun(BaseModel):
    command: str = Field(..., description="Command to execute")
    description: str = Field(..., description="Description of the command purpose")
    working_directory: str | None = Field(None, description="Working directory for the command")


class CodeTaskPlan(BaseModel):
    title: str = Field(..., description="Title of the code task")
    description: str = Field(..., description="Detailed description of the task")
    repository: str = Field(..., description="Repository URL to clone")
    branch: str | None = Field(None, description="Branch to use")
    file_changes: list[FileChange] = Field(..., description="File changes to make")
    commands: list[CommandToRun] = Field(..., description="Commands to run")
    test_commands: list[CommandToRun] | None = Field(None, description="Commands to verify the changes")


# Create the flow
flow = (
    Flow()
    # First: Set up progress monitoring
    .node(
        "progress_monitor",
        ProgressMonitorNode(
            settings=ProgressMonitorNodeSettings(
                report_interval=3.0,
                log_to_console=True,
            )
        ),
    )
    # Second: Parse the task and generate a plan
    .node(
        "task_analyzer",
        AIModelNode(
            resources=[
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "gpt-4o-mini"},
                    is_default=True,
                ),
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "claude-3-7-sonnet"},
                ),
            ],
            pre_events=[EventType.node_input_required],
            settings=AIModelNodeSettings(
                system_instructions=[
                    "You are a code task planner assisting with automated changes to a codebase.",
                    "Your job is to analyze a task description and break it down into specific steps that can be executed automatically.",
                    "Provide a structured plan including which files to create or modify and which commands to run.",
                ],
                prompt=Prompt(
                    role=PromptMessageRoleEnum.USER,
                    text=PromptText(
                        template=TextTemplate(
                            text=(
                                "I need to implement a task for the dhenara-agent package. Please help me create a plan.\n\n"
                                "Task description: {task_description}\n\n"
                                "Repository URL: {repo_url}\n"
                                "Branch: {branch}\n\n"
                                "Please analyze this task and create a detailed, structured plan for implementing it."
                            ),
                            variables={
                                "task_description": {},
                                "repo_url": {"default": "https://github.com/dhenara/dhen-agent.git"},
                                "branch": {"default": "main"},
                            },
                        ),
                    ),
                ),
                model_call_config=AIModelCallConfig(
                    structured_output=CodeTaskPlan,
                ),
            ),
            record_settings=NodeRecordSettings.with_outcome_format("json"),
        ),
    )
    # Third: Clone the repository
    .node(
        "repo_clone",
        CommandNode(
            settings=CommandNodeSettings(
                commands=[
                    "mkdir -p ${run_dir}/repo",
                    "git clone ${task_analyzer.outcome.repository} ${run_dir}/repo",
                    "cd ${run_dir}/repo && git checkout ${task_analyzer.outcome.branch || 'main'}",
                    "cd ${run_dir}/repo && ls -la",
                ],
                working_dir="${run_dir}",
                timeout=300,  # 5 minutes timeout for cloning
            )
        ),
    )
    # Fourth: Analyze the repository structure
    .node(
        "repo_analysis",
        FolderAnalyzerNode(
            settings=FolderAnalyzerSettings(
                path="${run_dir}/repo",
                max_depth=5,
                include_stats=True,
            )
        ),
    )
    # Fifth: Execute the necessary commands (setup, install, etc.)
    .node(
        "setup_commands",
        CommandNode(
            settings=CommandNodeSettings(
                commands=[
                    "${command}",
                ],
                working_dir="${run_dir}/repo",
                timeout=600,  # 10 minutes timeout
                fail_fast=False,  # Continue even if some commands fail
            )
        ),
    )
    # Sixth: Create or modify files according to the plan
    .node(
        "implement_changes",
        FileOperationNode(
            settings=FileOperationNodeSettings(
                base_directory="${run_dir}/repo",
                operations=[],  # Will be populated dynamically
            )
        ),
    )
    # Seventh: Run tests or validation commands
    .node(
        "verify_changes",
        CommandNode(
            settings=CommandNodeSettings(
                commands=[
                    "${command}",
                ],
                working_dir="${run_dir}/repo",
                timeout=300,  # 5 minutes timeout
            )
        ),
    )
    # Eighth: Commit the changes
    .node(
        "commit_changes",
        CommandNode(
            settings=CommandNodeSettings(
                commands=[
                    "cd ${run_dir}/repo && git add .",
                    "cd ${run_dir}/repo && git status",
                    'cd ${run_dir}/repo && git config --local user.email "agent@dhenara.com"',
                    'cd ${run_dir}/repo && git config --local user.name "Dhenara Agent"',
                    'cd ${run_dir}/repo && git commit -m "${commit_message}"',
                ],
                working_dir="${run_dir}",
            )
        ),
    )
    # Ninth: Summarize the changes made
    .node(
        "summarize_changes",
        AIModelNode(
            resources=[
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "gpt-4o-mini"},
                    is_default=True,
                ),
            ],
            settings=AIModelNodeSettings(
                system_instructions=[
                    "You are a technical writer creating a summary of code changes.",
                    "Provide a clear, concise summary of the changes that were made.",
                ],
                prompt=Prompt.with_dad_text(
                    text=(
                        "Please summarize the changes made to implement the following task:\n\n"
                        "Task: ${task_analyzer.outcome.description}\n\n"
                        "The following files were modified:\n${implement_changes.outcome.results | join('\n- ')}\n\n"
                        "Verification results:\n${verify_changes.outcome.results | join('\n- ')}\n\n"
                        "Provide a professional summary of the changes, focusing on what was implemented and how it fulfills the task requirements."
                    ),
                ),
                model_call_config=AIModelCallConfig(
                    test_mode=False,
                ),
            ),
            record_settings=NodeRecordSettings.with_outcome_format("text"),
        ),
    )
)
