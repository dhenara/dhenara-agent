# ruff:noqa: E501
from pydantic import BaseModel, Field

from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    EventType,
    FileOperationNode,
    FileOperationNodeSettings,
    Flow,
    FolderAnalyzerNode,
    FolderAnalyzerSettings,
    NodeRecordSettings,
)
from dhenara.agent.dsl.inbuilt.flow_nodes.file_operation.types import FileOperation
from dhenara.ai.types import (
    AIModelCallConfig,
    ObjectTemplate,
    Prompt,
    ResourceConfigItem,
)


class SingleShotCodeChanges(BaseModel):
    file_operations: list[FileOperation] = Field(..., description="File changes to make")
    description: str = Field(..., description="Precise description of changes in markdown format")
    # commands: list[CommandToRun] = Field(..., description="Commands to run")
    # test_commands: list[CommandToRun] | None = Field(
    #    None, description="Commands to verify the changes"
    # )


# Create the flow for a single-shot coder
flow = (
    Flow()
    ## Clone the repository
    # .node(
    #    "repo_clone",
    #    CommandNode(
    #        settings=CommandNodeSettings(
    #            commands=[
    #                "mkdir -p $expr{run_dir}/repo",
    #                "git clone $expr{repo_url} $expr{run_dir}/repo",
    #                "cd $expr{run_dir}/repo && git checkout $expr{branch || 'main'}",
    #                "cd $expr{run_dir}/repo && ls -la",
    #            ],
    #            working_dir="$expr{run_dir}",
    #            timeout=300,  # 5 minutes timeout for cloning
    #        )
    #    ),
    # )
    # Analyze the repository structure
    .node(
        "repo_analysis",
        FolderAnalyzerNode(
            settings=FolderAnalyzerSettings(
                path="$expr{run_root}/global_data/repo/src",
                # path="$expr{run_root}/global_data/repo/src/dhenara/agent/dsl/base/utils",
                max_depth=20,
                include_stats=False,
                respect_gitignore=True,
                read_content=True,
                max_words_per_file=None,  # Read all
                max_total_words=None,
                generate_tree_diagram=True,
            )
        ),
    )
    # Single-shot coding solution
    .node(
        "generate_solution",
        AIModelNode(
            resources=ResourceConfigItem.with_model("claude-3-7-sonnet"),
            # resources=ResourceConfigItem.with_model("gemini-2.0-flash-lite"),
            # resources=ResourceConfigItem.with_model("claude-3-5-haiku"),
            # resources=ResourceConfigItem.with_model("gpt-4o-mini"),
            pre_events=[EventType.node_input_required],
            settings=AIModelNodeSettings(
                system_instructions=[
                    "You are a precise code modification assistant that produces minimal changes to a codebase.",
                    "Your task is to generate the exact file operations necessary to implement requested changes - nothing more, nothing less.",
                    "",
                    "CRITICAL REQUIREMENTS:",
                    "- Group all modifications for the same file together in a single operation.",
                    "- Use EXACT patterns that uniquely identify edit points.",
                    "- Maintain correct indentation in all content.",
                    "- Do not duplicate existing code in bulk unless absolutely necessary.",
                    "- Ensure patterns match only once - expand context when needed.",
                    "- For sequential modifications, account for earlier changes to the same file.",
                    "",
                    "FORMAT SPECIFICATIONS:",
                    "- For new files: Use 'create_file' with complete content.",
                    "- For modifying file contents: Use 'edit_file' with exact match patterns.",
                    "- For selective content deletions: Use 'edit_file' with empty content string.",
                    "- For directories: Use 'create_directory' or 'delete_directory.'",
                    "",
                    "TOKEN MANAGEMENT:",
                    "- Prioritize complete, structured output over quantity",
                    "- Focus on core functionality first if token limits are a concern",
                ],
                prompt=Prompt.with_dad_text(
                    text=(
                        "I need you to implement the following task for the Dhenara agent package:"
                        ""
                        "Task: $var{task_description}"
                        ""
                        "Current repository structure and relevant files:"
                        ""
                        "$expr{repo_analysis.outcome.analysis}"
                        ""
                        "YOUR RESPONSE MUST:"
                        "1. Include only the necessary file operations to implement the task"
                        "2. Group all modifications to the same file in one operation"
                        "3. Use unique matching patterns that won't match multiple locations"
                        "4. Ensure operations can be applied programmatically without human intervention"
                        ""
                    ),
                    variables={
                        "task_description": {"default": "Generate test"},
                    },
                    disable_checks=True,
                ),
                model_call_config=AIModelCallConfig(
                    structured_output=SingleShotCodeChanges,
                    max_output_tokens=16000,
                    # reasoning=True,
                    # max_reasoning_tokens=4000,
                    options={
                        # "temperature": 0.1,
                    },
                    test_mode=False,
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
                # base_directory="$expr{run_dir}/repo",
                base_directory="$expr{run_root}/global_data/repo/src",
                operations_template=ObjectTemplate(
                    expression="$expr{generate_solution.outcome.structured.file_operations}",
                ),
            )
        ),
    )
)
"""
    # Run any provided test commands
    .node(
        "run_commands",
        CommandNode(
            settings=CommandNodeSettings(
                commands_from_list="$expr{generate_solution.outcome.commands}",
                working_dir="$expr{run_dir}/repo",
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
                    "cd $expr{run_dir}/repo && git add .",
                    "cd $expr{run_dir}/repo && git status",
                    'cd $expr{run_dir}/repo && git config --local user.email "agent@dhenara.com"',
                    'cd $expr{run_dir}/repo && git config --local user.name "Dhenara Agent"',
                    'cd $expr{run_dir}/repo && git commit -m "Implemented: $expr{commit_message}"',
                ],
                working_dir="$expr{run_dir}",
            )
        ),
    )
"""
