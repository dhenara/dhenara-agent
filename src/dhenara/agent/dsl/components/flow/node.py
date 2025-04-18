from dhenara.agent.dsl.base import (
    Executable,
    ExecutableNode,
    ExecutableNodeDefinition,
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
