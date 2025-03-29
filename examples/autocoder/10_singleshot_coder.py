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
from dhenara.agent.dsl.inbuilt.flow_nodes.file_operation.types import FileOperation
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


class CommandToRun(BaseModel):
    command: str = Field(..., description="Command to execute")
    description: str = Field(..., description="Description of the command purpose")
    working_directory: str | None = Field(None, description="Working directory for the command")


class FileChange(BaseModel):
    path: str = Field(..., description="Path to the file to be created or modified including file name")
    content: str = Field(..., description="Exact content of the file. Nothing extra.")
    operation: FileOperation
    description: str = Field(
        ...,
        description="Short description of the changes made to the file in less than 200 words",
    )


class CodeTaskPlan(BaseModel):
    title: str = Field(..., description="Title of the code task")
    description: str = Field(..., description="Detailed description of the task")
    repository: str = Field(..., description="Repository URL to clone")
    branch: str | None = Field(None, description="Branch to use")
    file_changes: list[FileChange] = Field(..., description="File changes to make")
    commands: list[CommandToRun] = Field(..., description="Commands to run")
    test_commands: list[CommandToRun] | None = Field(None, description="Commands to verify the changes")


class SingleShotCodeChanges(BaseModel):
    file_changes: list[FileChange] = Field(..., description="File changes to make")
    description: str = Field(..., description="Precise description of changes in less than 500 words.")
    commands: list[CommandToRun] = Field(..., description="Commands to run")
    test_commands: list[CommandToRun] | None = Field(None, description="Commands to verify the changes")


# Define the structured output model for the coding solution
class CodingSolution(BaseModel):
    file_changes: list[dict] = Field(
        ..., description="List of files to create or modify, with their full paths and content"
    )
    explanation: str = Field(..., description="Explanation of the solution implementation")
    commands: list[str] = Field(default=[], description="Optional commands to run to validate or test the solution")


# Create the flow for a single-shot coder
flow = (
    Flow()
    # Set up progress monitoring
    .node(
        "progress_monitor",
        ProgressMonitorNode(
            settings=ProgressMonitorNodeSettings(
                report_interval=3.0,
                log_to_console=True,
            )
        ),
    )
    # Clone the repository
    .node(
        "repo_clone",
        CommandNode(
            settings=CommandNodeSettings(
                commands=[
                    "mkdir -p ${run_dir}/repo",
                    "git clone ${repo_url} ${run_dir}/repo",
                    "cd ${run_dir}/repo && git checkout ${branch || 'main'}",
                    "cd ${run_dir}/repo && ls -la",
                ],
                working_dir="${run_dir}",
                timeout=300,  # 5 minutes timeout for cloning
            )
        ),
    )
    # Analyze the repository structure
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
    # Single-shot coding solution
    .node(
        "generate_solution",
        AIModelNode(
            resources=[
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "gpt-4o"},
                    is_default=True,
                ),
                ResourceConfigItem(
                    item_type=ResourceConfigItemTypeEnum.ai_model_endpoint,
                    query={ResourceQueryFieldsEnum.model_name: "claude-3-opus-20240229"},
                ),
            ],
            pre_events=[EventType.node_input_required],
            settings=AIModelNodeSettings(
                system_instructions=[
                    "You are a senior software engineer specializing in Python development.",
                    "Your task is to implement a coding solution in a single shot.",
                    "Analyze the codebase structure, understand the requirements, and provide a complete solution.",
                    "For each file that needs to be created or modified, provide the full file path and content.",
                    "Be thorough, precise, and ensure your solution is complete and ready to use with minimal human intervention.",
                ],
                prompt=Prompt(
                    role=PromptMessageRoleEnum.USER,
                    text=PromptText(
                        template=TextTemplate(
                            text=(
                                "I need you to implement the following task for the Dhenara agent package:\n\n"
                                "Task: {task_description}\n\n"
                                "Here's the current repository structure:\n\n"
                                "{repo_structure}\n\n"
                                "Please provide a complete solution that includes all necessary files with their content. "
                                "Don't just describe what to do - provide the exact code to implement this feature. "
                                "Return a structured solution with all file contents and explanations."
                            ),
                            variables={
                                "task_description": {},
                                "repo_structure": {"value": "${repo_analysis.outcome}"},
                            },
                        ),
                    ),
                ),
                model_call_config=AIModelCallConfig(
                    structured_output=CodingSolution,
                    temperature=0.1,
                    max_tokens=4000,
                ),
            ),
            record_settings=NodeRecordSettings.with_outcome_format("json"),
        ),
    )
    # Implement the solution (create/modify files)
    .node(
        "implement_solution",
        FileOperationNode(
            settings=FileOperationNodeSettings(
                base_directory="${run_dir}/repo",
                operations_from_json="${generate_solution.outcome.file_changes}",
            )
        ),
    )
    # Run any provided test commands
    .node(
        "run_commands",
        CommandNode(
            settings=CommandNodeSettings(
                commands_from_list="${generate_solution.outcome.commands}",
                working_dir="${run_dir}/repo",
                timeout=300,  # 5 minutes timeout
                fail_fast=False,  # Continue even if some commands fail
            )
        ),
    )
    # Commit the changes
    .node(
        "commit_changes",
        CommandNode(
            settings=CommandNodeSettings(
                commands=[
                    "cd ${run_dir}/repo && git add .",
                    "cd ${run_dir}/repo && git status",
                    'cd ${run_dir}/repo && git config --local user.email "agent@dhenara.com"',
                    'cd ${run_dir}/repo && git config --local user.name "Dhenara Agent"',
                    'cd ${run_dir}/repo && git commit -m "Implemented: ${commit_message}"',
                ],
                working_dir="${run_dir}",
            )
        ),
    )
)
