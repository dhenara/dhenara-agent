# ruff:noqa: E501
from pydantic import BaseModel, Field

from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    EventType,
    FileOperationNode,
    FileOperationNodeSettings,
    FlowDefinition,
    FolderAnalyzerNode,
    FolderAnalyzerSettings,
    NodeRecordSettings,
)
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import FileOperation, FolderAnalysisOperation
from dhenara.ai.types import (
    AIModelCallConfig,
    ObjectTemplate,
    Prompt,
    ResourceConfigItem,
)

# Common flow vars
repo_dir = "$expr{run_root}/global_data/repo"


class TaskImplementation(BaseModel):
    """
    Contains the concrete file operations to implement a specific task of the plan.
    This is the output generated after analyzing the context specified in the TaskSpec.
    """

    task_id: str = Field(
        ...,
        description=(
            "ID of the corresponding TaskSpec that this implements if it was given in the inputs, "
            "or a unique human readable task ID"
        ),
    )
    file_operations: list[FileOperation] = Field(
        ...,
        description="Ordered list of file operations to execute for this implementation task",
    )
    execution_commands: list[dict] | None = Field(
        None,
        description="Optional shell commands to run after file operations (e.g., for build or setup)",
    )
    verification_commands: list[dict] | None = Field(
        None,
        description="Optional commands to verify the changes work as expected",
    )

    def get_operation_summary(self) -> dict:
        """Returns a summary of the operations by type"""
        summary = {}
        for op in self.file_operations:
            if op.type in summary:
                summary[op.type] += 1
            else:
                summary[op.type] = 1
        return summary


# Implementation Agent Flow
implementation_flow = FlowDefinition()

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
# 1. Dynamic Folder Analysis (based on planner output)
implementation_flow.node(
    "dynamic_repo_analysis",
    FolderAnalyzerNode(
        # pre_events=[EventType.node_input_required],
        # settings=None,
        settings=FolderAnalyzerSettings(
            base_directory=repo_dir,
            operations=[
                FolderAnalysisOperation(
                    operation_type="analyze_folder",
                    path="src",
                    max_depth=100,
                    include_stats_and_meta=False,
                    respect_gitignore=True,
                    read_content=True,
                    content_read_mode="structure",
                    content_structure_detail_level="detailed",
                    include_content_preview=False,
                    max_words_per_file=None,  # Read all
                    max_total_words=None,
                    generate_tree_diagram=True,
                ),
            ],
        ),
    ),
)
# 2. Code Generation Node
implementation_flow.node(
    "code_generator",
    AIModelNode(
        resources=ResourceConfigItem.with_model("claude-3-7-sonnet"),
        pre_events=[EventType.node_input_required],
        settings=AIModelNodeSettings(
            system_instructions=[
                "You are a professional code implementation agent.",
                "Your task is to generate the exact file operations necessary to implement requested changes - nothing more, nothing less.",
                "You should generate precise file operations that can be executed automatically.",
                "The file operations should be any of create_file, edit_file, delete_file, create_directory, create_directory, move_file",
                "DO NOT use any of list_directory, search_files, get_file_metadata, list_allowed_directories",
                "",
                "For each file edit, provide exact patterns that uniquely identify the edit location.",
                "Ensure your implementation follows best practices and maintains code quality.",
                "To completely replace content of a file, do it in 2 steps with  delete_file and create_file operations instead doing it in a single edit_file."
                "",
                "TOKEN MANAGEMENT:",
                "- Prioritize complete, structured output over quantity",
                "- Focus on core functionality first if token limits are a concern",
            ],
            prompt=Prompt.with_dad_text(
                text=(
                    "Implement the following batch of code changes:\n\n"
                    "Task: $var{task_description} \n"
                    # "Context Files info :\n $expr{ $hier{dynamic_repo_analysis}.outcome.results }\n\n\n"
                    "Context Files info :\n $expr{py: [result.model_dump() for result in $hier{dynamic_repo_analysis}.outcome.results] }\n\n\n"
                    "Please implement these changes with precise file operations (create_file, edit_file etc) that can be executed programmatically without human intervention.\n"
                    "For each file edit, provide an exact pattern that uniquely identifies the location to edit.\n"
                    "Ensure your implementation maintains the existing code style and follows best practices.\n"
                    "Return a TaskImplementation object.\n"
                ),
                disable_checks=True,
            ),
            model_call_config=AIModelCallConfig(
                structured_output=TaskImplementation,
                max_output_tokens=8000,  # Limiting the output tokens to preserve context window
            ),
        ),
        record_settings=NodeRecordSettings.with_outcome_format("json"),
    ),
)


# 3. File Operation Node
implementation_flow.node(
    "code_generator_file_ops",
    FileOperationNode(
        settings=FileOperationNodeSettings(
            base_directory=repo_dir,
            operations_template=ObjectTemplate(
                expression="$expr{ $hier{code_generator}.outcome.structured.file_operations }",
            ),
            stage=True,
            commit=False,  # Commit handled in the coordinator
            commit_message="$var{run_id}: Implemented plan step",
        ),
    ),
)
