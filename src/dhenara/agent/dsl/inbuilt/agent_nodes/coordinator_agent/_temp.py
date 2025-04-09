from pydantic import Field

from dhenara.agent.dsl.components.agent import AgentFlow, AgentFlowExecutor, AgentNodeDefinition, AgentNodeSettings


class CoordinatorAgentSettings(AgentNodeSettings):
    """Settings for a coordinator agent that manages multiple agents."""

    agent_flow: AgentFlow = Field(
        ...,
        description="The agent flow to execute",
    )
    agent_flow_start_node: str | None = Field(
        default=None,
        description="Optional node ID to start agent flow execution from",
    )
    parallel_execution: bool = Field(
        default=False,
        description="Whether to execute agents in parallel",
    )
    fail_fast: bool = Field(
        default=True,
        description="Whether to stop on first failure",
    )


class CoordinatorAgentNode(AgentNodeDefinition):
    """A coordinator agent that orchestrates multiple agents."""

    agent_type: str = "coordinator_agent"
    settings: CoordinatorAgentSettings

    async def execute(self, agent_id, execution_context):
        # Create an agent flow executor
        agent_flow_executor = AgentFlowExecutor(
            id=agent_id,
            definition=self.settings.agent_flow,
            run_context=execution_context.run_context,
        )

        # Execute the agent flow
        results = await agent_flow_executor.execute(
            resource_config=execution_context.resource_config,
            start_node_id=self.settings.agent_flow_start_node,
        )

        return results
