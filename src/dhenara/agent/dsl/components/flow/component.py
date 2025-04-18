from typing import Any

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentExecutor,
    ExecutableComponent,
    ExecutableTypeEnum,
)
from dhenara.agent.dsl.components.flow import FlowExecutable, FlowExecutionContext, FlowNode
from dhenara.agent.observability.tracing.decorators.fns2 import trace_method


class FlowExecutionResult(ComponentExecutionResult):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow


class FlowDefinition(ComponentDefinition[FlowExecutable, FlowNode, FlowExecutionContext]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow
    node_class = FlowNode

    def subflow(
        self,
        id: str,  # noqa: A002
        definition: "FlowDefinition",
    ) -> "ComponentDefinition":
        """Add a component to the flow."""

        if not isinstance(definition, type(self)):
            raise ValueError(f"Unsupported type for body: {type(definition)}. Expected {type(self)}")

        self.elements.append(Flow(id=id, definition=definition))
        return self


class FlowExecutor(ComponentExecutor[FlowExecutable, FlowExecutionContext, FlowDefinition, FlowExecutionResult]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow
    context_class = FlowExecutionContext
    result_class = FlowExecutionResult
    logger_path: str = "dhenara.dad.flow"

    # Deinfe abstractmethod with proper trace name
    @trace_method("execute_flow")
    async def execute(
        self,
        start_node_id: str | None = None,
        parent_execution_context=None,
    ) -> dict[str, Any]:
        print(f"AJ: {self.__class__.__name__} execute: id: {self.id}")
        _result = await self._execute(
            start_node_id=start_node_id,
            parent_execution_context=parent_execution_context,
        )
        return _result


# ExecutableFlow
class Flow(ExecutableComponent[FlowExecutable, FlowDefinition, FlowExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow
