from typing import Union

from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentExecutor,
    ComponentInput,
    ComponentInputT,
    ComponentTypeEnum,
    Conditional,
    ExecutableComponent,
    ExecutableTypeEnum,
    ExecutionContext,
    ForEach,
)
from dhenara.agent.dsl.components.flow.component import Flow, FlowDefinition
from dhenara.ai.types.genai.dhenara.request.data import ObjectTemplate


class AgentInput(ComponentInput):
    pass


class AgentExecutionContext(ExecutionContext):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent


class AgentExecutionResult(ComponentExecutionResult):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent


class AgentExecutor(ComponentExecutor):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent
    component_type: ComponentTypeEnum = ComponentTypeEnum.agent  # Purely for tracing and logging
    input_model: ComponentInputT = AgentInput


class AgentDefinition(ComponentDefinition[AgentExecutionContext, AgentExecutionResult]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent
    context_class = AgentExecutionContext
    result_class = AgentExecutionResult
    logger_path: str = "dhenara.dad.agent"

    def flow(
        self,
        id: str,  # noqa: A002
        definition: FlowDefinition,
        variables: dict | None = None,
    ) -> "AgentDefinition":
        """Add a component to the agent."""

        if not isinstance(definition, FlowDefinition):
            raise ValueError(f"Unsupported type for body: {type(definition)}. Expected FlowDefinition")

        definition.update_vars(variables)
        self.elements.append(Flow(id=id, definition=definition))
        return self

    def subagent(
        self,
        id: str,  # noqa: A002
        definition: "AgentDefinition",
        variables: dict | None = None,
    ) -> "AgentDefinition":
        """Add a component to the agent."""

        if not isinstance(definition, AgentDefinition):
            raise ValueError(f"Unsupported type for body: {type(definition)}. Expected AgentDefinition")

        definition.update_vars(variables)
        self.elements.append(Agent(id=id, definition=definition))
        return self

    # TODO_FUTURE
    def conditional_flow(self):
        raise NotImplementedError("conditional_flow")

    # TODO_FUTURE
    def for_each_flow(self):
        raise NotImplementedError("for_each")

    def conditional(
        self,
        id: str,  # noqa: A002
        statement: ObjectTemplate,
        true_branch: "AgentDefinition",
        false_branch: Union["AgentDefinition", None] = None,
        true_branch_variables: dict | None = None,
        false_branch_variables: dict | None = None,
    ) -> "AgentDefinition":
        """Add a conditional branch to the agent."""

        if not isinstance(true_branch, AgentDefinition):
            raise ValueError(f"Unsupported subcomponent type: {type(true_branch)}. Expected AgentDefinition")

        if false_branch is not None and not isinstance(false_branch, AgentDefinition):
            raise ValueError(f"Unsupported subcomponent type: {type(false_branch)}. Expected AgentDefinition")

        true_branch.update_vars(true_branch_variables)
        if false_branch:
            false_branch.update_vars(false_branch_variables)

        _conditional = AgentConditional(
            statement=statement,
            true_branch=true_branch,
            false_branch=false_branch,
        )
        self.elements.append(Agent(id=id, definition=_conditional))
        return self

    def for_each(
        self,
        id: str,  # noqa: A002
        statement: ObjectTemplate,
        body: "AgentDefinition",
        max_iterations: int | None,
        item_var: str = "item",
        index_var: str = "index",
        start_index: int = 0,
        body_variables: dict | None = None,
    ) -> ForEach:
        """Add a loop to the agent."""

        if not isinstance(body, AgentDefinition):
            raise ValueError(f"Unsupported subcomponent type: {type(body)}. Expected AgentDefinition")

            # Foreach should take care of iter var
        _updated_body_vars = AgentForEach.check_iter_var_in_variable_update(body_variables)
        body.update_vars(_updated_body_vars)

        _foreach = AgentForEach(
            statement=statement,
            item_var=item_var,
            index_var=index_var,
            start_index=start_index,
            body=body,
            max_iterations=max_iterations,
        )
        self.elements.append(Agent(id=id, definition=_foreach))
        return self

    # Implementation of abstractmethod
    def get_executor_class(self):
        return AgentExecutor


class AgentConditional(Conditional, AgentDefinition):
    pass


class AgentForEach(ForEach, AgentDefinition):
    pass


# ExecutableAgent
class Agent(ExecutableComponent[AgentDefinition, AgentExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.agent
