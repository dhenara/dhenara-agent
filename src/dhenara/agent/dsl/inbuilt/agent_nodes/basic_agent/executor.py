import logging
from datetime import datetime
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from dhenara.agent.dsl.base import (
    ExecutableNodeDefinition,
    NodeExecutionResult,
    NodeID,
    NodeInput,
)
from dhenara.agent.dsl.components.agent import AgentExecutionContext, AgentNodeExecutor
from dhenara.agent.dsl.components.flow import Flow, FlowExecutor
from dhenara.agent.dsl.inbuilt.agent_nodes.basic_agent import (
    BasicAgentNodeInput,
    BasicAgentNodeOutcome,
    BasicAgentNodeOutput,
    BasicAgentNodeOutputData,
    basic_agent_node_tracing_profile,
)
from dhenara.agent.dsl.inbuilt.agent_nodes.defs import AgentNodeTypeEnum
from dhenara.agent.observability import log_with_context
from dhenara.agent.observability.tracing import trace_node
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)

BasicAgentNodeExecutionResult = NodeExecutionResult[
    BasicAgentNodeInput,
    BasicAgentNodeOutput,
    BasicAgentNodeOutcome,
]


class BasicAgentNodeExecutor(AgentNodeExecutor):
    node_type = AgentNodeTypeEnum.basic_agent.value
    input_model = None
    setting_model = None
    _tracing_profile = basic_agent_node_tracing_profile

    def get_result_class(self):
        return BasicAgentNodeExecutionResult

    @trace_node(AgentNodeTypeEnum.basic_agent.value)
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: AgentExecutionContext,
        node_input: NodeInput,
    ) -> BasicAgentNodeExecutionResult:
        result = await self._execute_flow_def(
            node_id=node_id,
            node_definition=node_definition,
            node_input=node_input,
            execution_context=execution_context,
        )
        return result

    async def _execute_flow_def(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: AgentExecutionContext,
    ) -> Any:
        """
        Handle the execution of a flow node.
        """

        flow_definition: Flow = node_definition.flow
        run_context = execution_context.run_context

        try:
            # Create orchestrator with resolved resources
            executor = FlowExecutor(
                id=node_id,  # By doing this, agent node_id will becombe flow's component id
                definition=flow_definition,
                run_context=run_context,
            )

            # Execute the flow, potentially starting from a specific node
            flow_result = await executor.execute(
                start_node_id=run_context.flow_start_node_id,
                parent_execution_context=execution_context,  # NOTE: pass parent
            )

            output_data = BasicAgentNodeOutputData(
                flow_execution_result=flow_result,
            )
            node_output = BasicAgentNodeOutput(data=output_data)
            node_outcome = BasicAgentNodeOutcome()

            return BasicAgentNodeExecutionResult(
                node_identifier=node_id,
                status=flow_result.execution_status,
                input=node_input,
                output=node_output,
                outcome=node_outcome,
                created_at=datetime.now(),
            )

        except PydanticValidationError as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Invalid inputs: {e!s}",
                {"root_id": str(run_context.root_component_id), "error": str(e)},
            )
            raise DhenaraAPIError(f"Invalid Inputs {e}")
