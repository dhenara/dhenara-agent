from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentExecutor,
    ExecutableComponent,
    ExecutableNodeDefinition,
    ExecutableTypeEnum,
    ExecutionContext,
    NodeDefT,
)
from dhenara.agent.dsl.components.flow import FlowNode


class FlowExecutionContext(ExecutionContext):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow


class FlowExecutionResult(ComponentExecutionResult):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow


class FlowExecutor(ComponentExecutor):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow


class FlowDefinition(ComponentDefinition[FlowExecutionContext, FlowExecutionResult]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow
    context_class = FlowExecutionContext
    result_class = FlowExecutionResult
    logger_path: str = "dhenara.dad.flow"

    # Factory methods for creating components
    def node(
        self,
        id: str,  # noqa: A002
        definition: NodeDefT,
    ) -> "ComponentDefinition":
        """Add a node to the flow."""

        if not isinstance(definition, ExecutableNodeDefinition) and definition.executable_type == self.executable_type:
            raise ValueError(
                f"Unsupported type for definition: {type(definition)}. "
                f"Expected a {self.executable_type}-NodeDefinition."
            )

        _node = FlowNode(id=id, definition=definition)
        self.elements.append(_node)
        return self

    def subflow(
        self,
        id: str,  # noqa: A002
        definition: "FlowDefinition",
    ) -> "ComponentDefinition":
        """Add a component to the flow."""

        if not isinstance(definition, FlowDefinition):
            raise ValueError(f"Unsupported type for body: {type(definition)}. Expected FlowDefinition")

        self.elements.append(Flow(id=id, definition=definition))
        return self

    # Implementaion of abstractmethod
    def get_component_executor(self):
        return FlowExecutor()  # TODO: Implement registry similar to node_executor_registry


# ExecutableFlow
class Flow(ExecutableComponent[FlowDefinition, FlowExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow
