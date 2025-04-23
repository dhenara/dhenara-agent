from typing import Union

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentExecutor,
    ComponentTypeEnum,
    Conditional,
    ExecutableComponent,
    ExecutableTypeEnum,
    ExecutionContext,
    ForEach,
    NodeDefT,
)
from dhenara.agent.dsl.components.flow import FlowNode


class FlowExecutionContext(ExecutionContext):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow


class FlowExecutionResult(ComponentExecutionResult):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow


class FlowExecutor(ComponentExecutor):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow
    component_type: ComponentTypeEnum = ComponentTypeEnum.flow  # Purely for tracing and logging


class FlowDefinition(ComponentDefinition[FlowExecutionContext, FlowExecutionResult]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow
    context_class = FlowExecutionContext
    result_class = FlowExecutionResult
    logger_path: str = "dhenara.dad.flow"

    def is_allowed_sub_components(self, inst) -> None:
        """Check for allowed definitions for this component."""
        if not isinstance(inst, FlowDefinition):
            raise ValueError(f"Unsupported subcomponent type: {type(inst)}. Expected FlowDefinition")

    # Factory methods for creating components
    def node(
        self,
        id: str,  # noqa: A002
        definition: NodeDefT,
    ) -> "ComponentDefinition":
        """Add a node to the flow."""

        _node = FlowNode(id=id, definition=definition)
        self.elements.append(_node)
        return self

    def subflow(
        self,
        id: str,  # noqa: A002
        definition: "FlowDefinition",
    ) -> "ComponentDefinition":
        """Add a component to the flow."""

        self.is_allowed_sub_components(definition)
        self.elements.append(Flow(id=id, definition=definition))
        return self

    # TODO: Cleanup
    def conditional(
        self,
        id: str,  # noqa: A002
        statement: str,
        then_branch: "ComponentDefinition",
        else_branch: Union["ComponentDefinition", None] = None,
    ) -> "ComponentDefinition":
        """Add a conditional branch to the flow."""

        self.is_allowed_sub_components(then_branch)
        if else_branch is not None:
            self.is_allowed_sub_components(else_branch)

        _conditional = Conditional(
            statement=statement,
            then_branch=then_branch,
            else_branch=else_branch,
        )
        self.elements.append(Flow(id=id, definition=_conditional))
        return self

    def for_each(
        self,
        id: str,  # noqa: A002
        statement: str,
        body: "ComponentDefinition",
        max_iterations: int | None,
        item_var: str = "item",
        index_var: str = "index",
        collect_results: bool = True,
    ) -> ForEach:
        """Add a loop to the flow."""

        self.is_allowed_sub_components(body)

        _foreach = FlowForEach(
            statement=statement,
            item_var=item_var,
            index_var=index_var,
            body=body,
            collect_results=collect_results,
            max_iterations=max_iterations,
        )
        self.elements.append(Flow(id=id, definition=_foreach))
        return self

    # Implementaion of abstractmethod
    def get_component_executor(self):
        return FlowExecutor()  # TODO: Implement registry similar to node_executor_registry


class FlowForEach(ForEach, FlowDefinition):
    pass


# ExecutableFlow
class Flow(ExecutableComponent[FlowDefinition, FlowExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow
