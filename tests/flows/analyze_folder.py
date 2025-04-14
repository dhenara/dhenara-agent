from dhenara.agent.dsl import (
    CommandNode,
    CommandNodeSettings,
    Flow,
    FolderAnalyzerNode,
    FolderAnalyzerSettings,
)
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import FolderAnalysisOperation

flow = Flow()
flow.node(
    "list_files",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "ls -la $expr{run_dir}",
                "mkdir $expr{run_dir}/$expr{node_id}",
                "mkdir $expr{run_dir}/$expr{node_id}/temp_dir",
            ],
            working_dir="$expr{run_dir}",
        )
    ),
)
flow.node(
    "analyze_run_dir",
    FolderAnalyzerNode(
        settings=FolderAnalyzerSettings(
            base_directory="$expr{run_dir}",
            operations=[
                FolderAnalysisOperation(
                    operation_type="analyze_folder",
                    path="",
                    # path="$expr{run_root}/global_data/repo/src/dhenara/agent/dsl/base/utils",
                    max_depth=3,
                    include_stats_and_meta=True,
                ),
            ],
        ),
    ),
)
flow.node(
    "move_dir",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "ls -la $expr{run_dir}",
                "mkdir $expr{run_dir}/$expr{node_id}",
                "mv $expr{run_dir}/list_files/temp_dir $expr{run_dir}/$expr{node_id}/.",
            ],
            working_dir="$expr{run_dir}",
        )
    ),
)
