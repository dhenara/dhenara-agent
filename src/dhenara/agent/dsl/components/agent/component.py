from dhenara.agent.dsl.base import (
    ComponentDefinition,
    ComponentExecutionResult,
    ComponentExecutor,
    ExecutableComponent,
    ExecutableTypeEnum,
    ExecutionContext,
)
from dhenara.agent.dsl.components.flow.component import Flow, FlowDefinition


class AgentExecutionContext(ExecutionContext):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent


class AgentExecutionResult(ComponentExecutionResult):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent


class AgentExecutor(ComponentExecutor):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent


class AgentDefinition(ComponentDefinition[AgentExecutionContext, AgentExecutionResult]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent
    context_class = AgentExecutionContext
    result_class = AgentExecutionResult
    logger_path: str = "dhenara.dad.agent"

    def flow(
        self,
        id: str,  # noqa: A002
        definition: FlowDefinition,
    ) -> "ComponentDefinition":
        """Add a component to the flow."""

        if not isinstance(definition, FlowDefinition):
            raise ValueError(f"Unsupported type for body: {type(definition)}. Expected FlowDefinition")

        self.elements.append(Agent(id=id, definition=definition))
        return self

    def subagent(
        self,
        id: str,  # noqa: A002
        definition: "AgentDefinition",
    ) -> "ComponentDefinition":
        """Add a component to the flow."""

        if not isinstance(definition, AgentDefinition):
            raise ValueError(f"Unsupported type for body: {type(definition)}. Expected AgentDefinition")

        self.elements.append(Flow(id=id, definition=definition))
        return self

    # Implementaion of abstractmethod
    def get_component_executor(self):
        return AgentExecutor()  # TODO: Implement registry similar to node_executor_registry


# ExecutableAgent
class Agent(ExecutableComponent[AgentDefinition, AgentExecutionContext]):
    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.flow
