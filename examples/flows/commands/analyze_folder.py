from dhenara.agent.dsl import (
    CommandNode,
    CommandNodeSettings,
    Flow,
    FolderAnalyzerNode,
    FolderAnalyzerSettings,
)

flow = Flow()
flow.node(
    "list_files",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "ls -la ${run_dir}",
                "mkdir ${run_dir}/${node_id}/temp_dir",
            ],
            working_dir="${run_dir}",
        )
    ),
)
flow.node(
    "analyze_run_dir",
    FolderAnalyzerNode(
        settings=FolderAnalyzerSettings(
            path="${run_dir}",
            max_depth=3,
            include_stats=True,
        )
    ),
)
flow.node(
    "move_dir",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "ls -la ${run_dir}",
                "mv ${run_dir}/list_files/temp_dir ${run_dir}/${node_id}/.",
            ],
            working_dir="${run_dir}",
        )
    ),
)
