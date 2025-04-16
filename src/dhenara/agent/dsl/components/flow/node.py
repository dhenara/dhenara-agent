from typing import ClassVar

from dhenara.agent.dsl.base import (
    Executable,
    ExecutableBlock,
    ExecutableNode,
    ExecutableNodeDefinition,
    ExecutableReference,
    ExecutableTypeEnum,
    NodeExecutor,
)
from dhenara.agent.dsl.components.flow import FlowExecutionContext


class FlowExecutable(Executable):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow


class FlowNodeDefinition(ExecutableNodeDefinition[FlowExecutionContext]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow


class FlowNodeExecutor(NodeExecutor):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow


class FlowNode(ExecutableNode[FlowExecutable, FlowNodeDefinition, FlowExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow


class FlowBlock(ExecutableBlock[FlowExecutable, FlowNode, FlowExecutionContext]):
    node_class: ClassVar[type[FlowNode]] = FlowNode

    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow


class FlowReference(ExecutableReference):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow
