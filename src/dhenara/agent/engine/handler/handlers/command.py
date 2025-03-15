import asyncio
from typing import Any

from dhenara.agent.engine.handler import NodeHandler
from dhenara.agent.types.flow import FlowContext, FlowNode
from dhenara.ai.types.resource import ResourceConfig


class CommandHandler(NodeHandler):
    def __init__(
        self,
    ):
        super().__init__(identifier="command_handler")

    async def handle(self, flow_node: FlowNode, context: FlowContext, resource_config: ResourceConfig) -> Any:
        # Use asyncio.create_subprocess_shell for non-blocking command execution
        process = await asyncio.create_subprocess_shell(
            flow_node.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for the command to complete and get output
        stdout, stderr = await process.communicate()

        # You may want to return the results or store them in the context
        return {
            "returncode": process.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
        }
