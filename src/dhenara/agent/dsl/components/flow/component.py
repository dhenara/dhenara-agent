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
from dhenara.ai.types.genai.dhenara.request.data import ObjectTemplate


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

    # Factory methods for creating components
    def node(
        self,
        id: str,  # noqa: A002
        definition: NodeDefT,
    ) -> "FlowDefinition":
        """Add a node to the flow."""

        _node = FlowNode(id=id, definition=definition)
        self.elements.append(_node)
        return self

    def subflow(
        self,
        id: str,  # noqa: A002
        definition: "FlowDefinition",
        variables: dict | None = None,
    ) -> "FlowDefinition":
        """Add a component to the flow."""

        if not isinstance(definition, FlowDefinition):
            raise ValueError(f"Unsupported subcomponent type: {type(definition)}. Expected FlowDefinition")

        definition.update_vars(variables)
        self.elements.append(Flow(id=id, definition=definition))
        return self

    def conditional(
        self,
        id: str,  # noqa: A002
        statement: ObjectTemplate,
        true_branch: "FlowDefinition",
        false_branch: Union["FlowDefinition", None] = None,
    ) -> "FlowDefinition":
        """Add a conditional branch to the flow."""

        if not isinstance(true_branch, FlowDefinition):
            raise ValueError(f"Unsupported subcomponent type: {type(true_branch)}. Expected FlowDefinition")
        if false_branch is not None and not isinstance(false_branch, FlowDefinition):
            raise ValueError(f"Unsupported subcomponent type: {type(false_branch)}. Expected FlowDefinition")

        _conditional = FlowConditional(
            statement=statement,
            true_branch=true_branch,
            false_branch=false_branch,
        )
        self.elements.append(Flow(id=id, definition=_conditional))
        return self

    def for_each(
        self,
        id: str,  # noqa: A002
        statement: ObjectTemplate,
        body: "FlowDefinition",
        max_iterations: int | None,
        item_var: str = "item",
        index_var: str = "index",
        start_index: int = 0,
    ) -> ForEach:
        """Add a loop to the flow."""

        if not isinstance(body, FlowDefinition):
            raise ValueError(f"Unsupported subcomponent type: {type(body)}. Expected FlowDefinition")

        _foreach = FlowForEach(
            statement=statement,
            item_var=item_var,
            index_var=index_var,
            start_index=start_index,
            body=body,
            max_iterations=max_iterations,
        )
        self.elements.append(Flow(id=id, definition=_foreach))
        return self

    # Implementaion of abstractmethod
    def get_component_executor(self):
        return FlowExecutor()  # TODO: Implement registry similar to node_executor_registry


class FlowConditional(Conditional, FlowDefinition):
    pass


class FlowForEach(ForEach, FlowDefinition):
    pass


# ExecutableFlow
class Flow(ExecutableComponent[FlowDefinition, FlowExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow
