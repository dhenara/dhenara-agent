from dhenara.agent.types import (
    CommandSettings,
    ExecutionStrategyEnum,
    FlowDefinition,
    FlowNode,
    FlowNodeTypeEnum,
    FolderAnalyzerSettings,
    GitRepoAnalyzerSettings,
    ResponseProtocolEnum,
)

flow_definition = FlowDefinition(
    execution_strategy=ExecutionStrategyEnum.sequential,
    response_protocol=ResponseProtocolEnum.HTTP,
    nodes=[
        # Execute command to list files
        FlowNode(
            order=0,
            identifier="list_files",
            type=FlowNodeTypeEnum.command,
            command_settings=CommandSettings(
                commands=[
                    "ls -la {dh_input_dir}",
                    "find {dh_input_dir} -type f -name '*.py' | wc -l",
                ],
                working_dir="{dh_run_dir}",
                timeout=30,
            ),
        ),
        # Analyze a folder
        FlowNode(
            order=1,
            identifier="analyze_folder",
            type=FlowNodeTypeEnum.folder_analyzer,
            folder_analyzer_settings=FolderAnalyzerSettings(
                path="{dh_input_dir}",
                max_depth=3,
                include_hidden=False,
                include_stats=True,
            ),
        ),
        # Analyze a git repository if it exists
        FlowNode(
            order=2,
            identifier="analyze_git_repo",
            type=FlowNodeTypeEnum.git_repo_analyzer,
            git_repo_analyzer_settings=GitRepoAnalyzerSettings(
                path="{dh_project_root}",
                max_depth=2,
                include_git_history=True,
                max_commits=20,
                include_branch_info=True,
            ),
        ),
    ],
)
