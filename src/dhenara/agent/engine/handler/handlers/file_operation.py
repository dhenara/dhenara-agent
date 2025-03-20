# FileOperationHandler for creating and modifying files
import json
import logging
import os
from pathlib import Path
from typing import Any

from dhenara.agent.dsl.base import ExecutableNodeDefinition, ExecutionContext
from dhenara.agent.engine.handler import NodeHandler
from dhenara.agent.types import FlowNodeOutput, NodeInput
from dhenara.ai.types.resource import ResourceConfig

logger = logging.getLogger(__name__)


class FileOperationHandler(NodeHandler):
    """Handler for file operations"""

    def __init__(self):
        super().__init__(identifier="file_operation_handler")

    async def handle(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        resource_config: ResourceConfig,
    ) -> Any:
        # Extract file operations from input
        file_ops_input = node_input.content.get_content()

        try:
            # Parse the file operations (expected JSON format)
            file_ops = json.loads(file_ops_input)
            base_dir = file_ops.get("base_directory", ".")
            operations = file_ops.get("operations", [])

            results = []
            for operation in operations:
                op_type = operation.get("type")
                path = operation.get("path")
                full_path = Path(base_dir) / path

                if op_type == "create_directory":
                    full_path.mkdir(parents=True, exist_ok=True)
                    results.append(
                        {
                            "type": "create_directory",
                            "path": path,
                            "success": True,
                        }
                    )

                elif op_type == "create_file":
                    content = operation.get("content", "")
                    full_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(full_path, "w") as f:  # noqa: ASYNC230: TODO_FUTURE
                        f.write(content)

                    results.append(
                        {
                            "type": "create_file",
                            "path": path,
                            "success": True,
                        }
                    )

                elif op_type == "modify_file":
                    if not full_path.exists():
                        results.append(
                            {
                                "type": "modify_file",
                                "path": path,
                                "success": False,
                                "error": "File does not exist",
                            }
                        )
                        continue

                    content = operation.get("content", "")
                    with open(full_path, "w") as f:  # noqa: ASYNC230: TODO_FUTURE
                        f.write(content)

                    results.append(
                        {
                            "type": "modify_file",
                            "path": path,
                            "success": True,
                        }
                    )

                elif op_type == "delete":
                    if full_path.is_file():
                        os.remove(full_path)
                    elif full_path.is_dir():
                        import shutil

                        shutil.rmtree(full_path)

                    results.append(
                        {
                            "type": "delete",
                            "path": path,
                            "success": True,
                        }
                    )

            # Create node output
            return FlowNodeOutput(
                data={
                    "success": True,
                    "operations_count": len(operations),
                    "results": results,
                }
            )
        except Exception as e:
            logger.exception(f"File operation execution failed: {e}")
            return FlowNodeOutput(
                data={
                    "success": False,
                    "error": str(e),
                }
            )
