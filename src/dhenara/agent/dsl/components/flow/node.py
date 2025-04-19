from dhenara.agent.dsl.base import (
    ExecutableNode,
    ExecutableNodeDefinition,
    ExecutableTypeEnum,
    ExecutionContext,
    NodeExecutor,
)


class FlowNodeExecutionContext(ExecutionContext):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow_node


# class FlowExecutable():
#    @property
#    def executable_type(self) -> ExecutableTypeEnum:
#        return ExecutableTypeEnum.flow_node


class FlowNodeDefinition(ExecutableNodeDefinition[FlowNodeExecutionContext]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow_node


class FlowNodeExecutor(NodeExecutor):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow_node


class FlowNode(ExecutableNode[FlowNodeDefinition, FlowNodeExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow_node
