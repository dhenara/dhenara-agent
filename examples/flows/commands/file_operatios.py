# ruff: noqa: E501
from dhenara.agent.dsl import (
    CommandNode,
    CommandNodeSettings,
    FileModificationContent,
    FileOperation,
    FileOperationNode,
    FileOperationNodeSettings,
    Flow,
)

# Create a flow to test all file operations
flow = Flow()

# 1. First, create a simple directory structure and a file to work with
flow.node(
    "setup_environment",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "mkdir -p ${run_dir}/test_files",
                "echo 'Hello, this is a test file.\nThis line will stay.\n/* REPLACE_START */This content will be replaced/* REPLACE_END */\nThis is the footer.' > ${run_dir}/test_files/sample.txt",
                "echo 'Current directory structure:' && ls -la ${run_dir}/test_files",
            ],
            working_dir="${run_dir}",
        )
    ),
)

# 2. Test creating directories
flow.node(
    "create_directories",
    FileOperationNode(
        settings=FileOperationNodeSettings(
            base_directory="${run_dir}/test_files",
            operations=[
                FileOperation(
                    type="create_directory",
                    path="dir1",
                    content=None,
                ),
                FileOperation(
                    type="create_directory",
                    path="dir2/nested/deep",
                    content=None,
                ),
            ],
        )
    ),
)

# 3. Verify directory creation
flow.node(
    "verify_directories",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "echo 'Directory structure after creation:' && ls -la ${run_dir}/test_files",
                "if [ -d '${run_dir}/test_files/dir1' ]; then echo 'dir1 created successfully'; else echo 'dir1 creation failed'; fi",
                "if [ -d '${run_dir}/test_files/dir2/nested/deep' ]; then echo 'nested directories created successfully'; else echo 'nested directories creation failed'; fi",
            ],
            working_dir="${run_dir}",
        )
    ),
)

# 4. Test creating files
flow.node(
    "create_files",
    FileOperationNode(
        settings=FileOperationNodeSettings(
            base_directory="${run_dir}/test_files",
            operations=[
                FileOperation(
                    type="create_file",
                    path="dir1/file1.txt",
                    content="This is the content of file1.txt",
                ),
                FileOperation(
                    type="create_file",
                    path="dir2/nested/file2.txt",
                    content="This is the content of file2.txt\nWith multiple lines",
                ),
                FileOperation(
                    type="create_file",
                    path="empty_file.txt",
                    content="",
                ),
            ],
        )
    ),
)

# 5. Verify file creation
flow.node(
    "verify_files",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "echo 'Checking created files:'",
                "echo 'File1 content:' && cat ${run_dir}/test_files/dir1/file1.txt",
                "echo 'File2 content:' && cat ${run_dir}/test_files/dir2/nested/file2.txt",
                "echo 'Empty file exists:' && ls -la ${run_dir}/test_files/empty_file.txt",
            ],
            working_dir="${run_dir}",
        )
    ),
)

# 6. Test modifying files
flow.node(
    "modify_files",
    FileOperationNode(
        settings=FileOperationNodeSettings(
            base_directory="${run_dir}/test_files",
            operations=[
                FileOperation(
                    type="modify_file",
                    path="sample.txt",
                    content=FileModificationContent(
                        start_point_match="/* REPLACE_START */",
                        end_point_match="/* REPLACE_END */",
                        content="This is the new modified content",
                    ),
                ),
                FileOperation(
                    type="modify_file",
                    path="dir1/file1.txt",
                    content=FileModificationContent(
                        start_point_match="This is",
                        end_point_match="file1.txt",
                        content=" the updated content of ",
                    ),
                ),
            ],
        )
    ),
)

# 7. Verify file modifications
flow.node(
    "verify_modifications",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "echo 'Checking modified files:'",
                "echo 'Modified sample.txt:' && cat ${run_dir}/test_files/sample.txt",
                "echo 'Modified file1.txt:' && cat ${run_dir}/test_files/dir1/file1.txt",
            ],
            working_dir="${run_dir}",
        )
    ),
)

# 8. Test deleting files
flow.node(
    "delete_files",
    FileOperationNode(
        settings=FileOperationNodeSettings(
            base_directory="${run_dir}/test_files",
            operations=[
                FileOperation(
                    type="delete_file",
                    path="empty_file.txt",
                    content=None,
                ),
                FileOperation(
                    type="delete_file",
                    path="dir2/nested/file2.txt",
                    content=None,
                ),
            ],
        )
    ),
)

# 9. Verify file deletion
flow.node(
    "verify_file_deletion",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "echo 'Checking after file deletion:'",
                "if [ -f '${run_dir}/test_files/empty_file.txt' ]; then echo 'empty_file.txt still exists (FAILURE)'; else echo 'empty_file.txt deleted successfully'; fi",
                "if [ -f '${run_dir}/test_files/dir2/nested/file2.txt' ]; then echo 'file2.txt still exists (FAILURE)'; else echo 'file2.txt deleted successfully'; fi",
            ],
            working_dir="${run_dir}",
        )
    ),
)

# 10. Test deleting directories
flow.node(
    "delete_directories",
    FileOperationNode(
        settings=FileOperationNodeSettings(
            base_directory="${run_dir}/test_files",
            operations=[
                FileOperation(
                    type="delete_directory",
                    path="dir2",
                    content=None,
                ),
            ],
        )
    ),
)

# 11. Verify directory deletion and final state
flow.node(
    "verify_final_state",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "echo 'Final directory structure:' && ls -la ${run_dir}/test_files",
                "if [ -d '${run_dir}/test_files/dir2' ]; then echo 'dir2 still exists (FAILURE)'; else echo 'dir2 deleted successfully'; fi",
                "echo 'Remaining file contents:'",
                "echo 'sample.txt:' && cat ${run_dir}/test_files/sample.txt",
                "echo 'file1.txt:' && cat ${run_dir}/test_files/dir1/file1.txt",
            ],
            working_dir="${run_dir}",
        )
    ),
)

# 12. Test edge cases
flow.node(
    "test_edge_cases",
    FileOperationNode(
        settings=FileOperationNodeSettings(
            base_directory="${run_dir}/test_files",
            operations=[
                # Try to modify a non-existent file
                FileOperation(
                    type="modify_file",
                    path="non_existent.txt",
                    content=FileModificationContent(
                        start_point_match="start",
                        end_point_match="end",
                        content="content",
                    ),
                ),
                # Try to delete a non-existent file
                FileOperation(
                    type="delete_file",
                    path="another_non_existent.txt",
                    content=None,
                ),
                # Try to create a file in a non-existent directory with auto-creation
                FileOperation(
                    type="create_file",
                    path="new_dir/auto_created.txt",
                    content="This file should be created along with its parent directory",
                ),
            ],
        )
    ),
)

# 13. Verify edge case results
flow.node(
    "verify_edge_cases",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "echo 'Edge case results:'",
                "if [ -f '${run_dir}/test_files/new_dir/auto_created.txt' ]; then echo 'auto_created.txt was created successfully with its directory'; else echo 'auto_created.txt creation failed'; fi",
                "if [ -f '${run_dir}/test_files/new_dir/auto_created.txt' ]; then cat ${run_dir}/test_files/new_dir/auto_created.txt; fi",
            ],
            working_dir="${run_dir}",
        )
    ),
)

# 14. Cleanup
flow.node(
    "cleanup",
    CommandNode(
        settings=CommandNodeSettings(
            commands=[
                "echo 'Cleaning up test directory'",
                "rm -rf ${run_dir}/test_files",
                "echo 'Test completed successfully!'",
            ],
            working_dir="${run_dir}",
        )
    ),
)

# Set up flow execution order
# flow.edge("setup_environment", "create_directories")
# flow.edge("create_directories", "verify_directories")
# flow.edge("verify_directories", "create_files")
# flow.edge("create_files", "verify_files")
# flow.edge("verify_files", "modify_files")
# flow.edge("modify_files", "verify_modifications")
# flow.edge("verify_modifications", "delete_files")
# flow.edge("delete_files", "verify_file_deletion")
# flow.edge("verify_file_deletion", "delete_directories")
# flow.edge("delete_directories", "verify_final_state")
# flow.edge("verify_final_state", "test_edge_cases")
# flow.edge("test_edge_cases", "verify_edge_cases")
# flow.edge("verify_edge_cases", "cleanup")
