import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, TypeVar

from dhenara.agent.dsl.base import (
    ExecutableNodeDefinition,
    ExecutableTypeEnum,
    ExecutionContext,
    ExecutionStatusEnum,
    ExecutionStrategyEnum,
    NodeExecutionResult,
    NodeID,
    NodeInput,
    NodeSettings,
)
from dhenara.agent.dsl.events import NodeExecutionCompletedEvent, NodeInputRequiredEvent
from dhenara.agent.observability import log_with_context, record_metric

logger = logging.getLogger(__name__)

ContextT = TypeVar("ContextT", bound=ExecutionContext)


class NodeExecutor(ABC):
    """Base handler for executing flow nodes.
    All node type handlers should inherit from this class and implement
    the handle method to process their specific node type.

    **** NOTE ****
    Implementation should be stateless,
    as only a single instance will be created for the entire run.

    """

    node_type: str
    executable_type: ExecutableTypeEnum
    input_model: type[NodeInput] | None
    setting_model: type[NodeSettings]

    def __init__(self):
        self.logger = logging.getLogger(f"dhenara.dad.dsl.node_executor.{self.node_type}")

    @abstractmethod
    def get_result_class(self):
        """Get the executon resutl class. Used to reload previous results."""
        pass

    async def get_input_for_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
    ) -> NodeInput:
        """Get input for a node, trying static inputs first then event handlers."""
        # Check static inputs first
        if node_id in execution_context.run_context.static_inputs:
            log_with_context(self.logger, logging.DEBUG, f"Using static input for node {node_id}")
            return execution_context.run_context.static_inputs[node_id]

        if node_definition.trigger_pre_execute_input_required:
            node_input = await self.tirgger_event_node_input_required(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
            )
            return node_input

        log_with_context(self.logger, logging.DEBUG, f"Failed to fetch inputs for node {node_id}")
        return None

    # Inbuild  events
    async def tirgger_event_node_input_required(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
    ) -> NodeInput:
        # Request input via event
        event = NodeInputRequiredEvent(
            node_id=node_id,
            node_type=node_definition.node_type,
            node_def_settings=node_definition.settings,
        )
        await execution_context.run_context.event_bus.publish(event)

        node_input = None

        # Check if any handler provided input
        if event.handled and event.node_input:
            if isinstance(event.node_input, dict):
                try:
                    node_input = self.input_model(**event.node_input)
                except Exception as e:
                    logger.error(f"{node_id}: Error while validation node input dict vai event. {e}")

            elif isinstance(event.node_input, self.input_model):
                node_input = event.node_input

            logger.debug(f"{node_id}: Node input via event {event.type} is {node_input}")
        else:
            # No input provided by any handler
            logger.error(f"{node_id}: No input provided for node via event {event.type}")

        return node_input

    async def execute(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
    ) -> Any:
        log_with_context(
            self.logger,
            logging.DEBUG,
            "Waiting for node input",
            {"node_id": str(node_id), "node_type": node_definition.node_type},
        )

        node_input = None
        if node_definition.trigger_pre_execute_input_required:
            node_input = await self.get_input_for_node(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
            )

            log_with_context(self.logger, logging.DEBUG, "Node Input received", {"node_id": str(node_id)})

            if not isinstance(node_input, self.input_model):
                log_with_context(
                    self.logger,
                    logging.ERROR,
                    f"Input validation failed. Expected {self.input_model} but got {type(node_input)}",
                    {"node_id": str(node_id)},
                )
                raise ValueError(
                    f"Input validation failed. Expects type of {self.input_model} but got a type of {type(node_input)}"
                )

        # TODO: Also consider settings_overrride
        if node_definition.settings and node_definition.settings.sleep_before:
            await asyncio.sleep(node_definition.settings.sleep_before)

        # Record start time for metrics
        start_time = datetime.now()

        # TODO_FUTURE: Remove, as we record the result with input
        # Record input if configured
        # input_record_settings = node_definition.record_settings.input if node_definition.record_settings else None
        input_record_settings = None

        if input_record_settings and input_record_settings.enabled:
            input_data = node_input.model_dump() if hasattr(node_input, "model_dump") else node_input
            execution_context.artifact_manager.record_data(
                record_type="input",
                data=input_data,
                record_settings=input_record_settings,
                execution_context=execution_context,
            )

        # if self.is_streaming:
        #    # Configure streaming execution_context
        #    execution_context.streaming_contexts[execution_context.current_node_identifier] = StreamingContext(
        #        status=StreamingStatusEnum.STREAMING,
        #        completion_event=Event(),
        #    )
        #    execution_context.current_node_index = index
        #    # Execute streaming node
        #    result = await node_executor.handle(
        #        flow_node=flow_node,
        #        flow_node_input=flow_node_input,
        #        execution_context=execution_context,
        #    )
        #    if not isinstance(result, AsyncGenerator):
        #        execution_context.logger.error(
        #            f"A streaming node node_executor is expected to returned an AsyncGenerator not{type(result)}. "
        #            f"Node {flow_node.identifier}, node_executor {node_executor.identifier}"
        #        )
        #    return result

        # Execute the node
        result = await self.execute_node(
            node_id=node_id,
            node_definition=node_definition,
            node_input=node_input,
            execution_context=execution_context,
        )

        # Set the result in the execution context
        execution_context.set_result(node_id, result)

        # TODO: Check for straming result
        # if result is not None:  # Streaming case will return an async generator
        #    return result

        # Record metrics
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        record_metric(
            meter_name="dhenara.dad.node",
            metric_name="node_execution_duration",
            value=duration_ms,
            metric_type="histogram",
            attributes={
                "node_id": str(node_id),
                "node_type": node_definition.node_type,
            },
        )

        # Record success/failure metrics
        if result is not None:
            record_metric(
                meter_name="dhenara.dad.node",
                metric_name="node_execution_success",
                value=1,
                attributes={
                    "node_id": str(node_id),
                    "node_type": node_definition.node_type,
                },
            )
        else:
            record_metric(
                meter_name="dhenara.dad.node",
                metric_name="node_execution_failure",
                value=1,
                attributes={
                    "node_id": str(node_id),
                    "node_type": node_definition.node_type,
                },
            )

        log_with_context(
            self.logger,
            logging.DEBUG,
            f"Node Execution completed in {duration_ms:.2f}ms",
            {"node_id": str(node_id), "duration_ms": duration_ms, "has_result": result is not None},
        )

        if node_definition.trigger_execution_completed:
            event = NodeExecutionCompletedEvent(
                node_id=node_id,
                node_type=node_definition.node_type,
                node_outcome=execution_context.execution_results.get(node_id, {}).outcome,
            )
            await execution_context.run_context.event_bus.publish(event)

        # TODO: Also consider settings_overrride
        if node_definition.settings and node_definition.settings.sleep_after:
            asyncio.sleep(node_definition.settings.sleep_after)

        # Record results to storage
        return await self.record_results(
            node_id=node_id,
            node_definition=node_definition,
            execution_context=execution_context,
        )

    @abstractmethod
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
    ) -> Any:
        """
        Handle the execution of a flow node.
        """
        pass

    async def record_results(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ContextT,
    ) -> AsyncGenerator | None:
        if execution_context.artifact_manager:
            result: NodeExecutionResult | None = execution_context.execution_results.get(node_id, None)

            if not result:
                logger.info("No result found in execution context. Skipping records")
                return False

            execution_context.updated_at = datetime.now()
            # Get record settings from the node if available
            result_record_settings = None
            result_record_settings = None

            if node_definition.record_settings:
                result_record_settings = node_definition.record_settings.result
                outcome_record_settings = node_definition.record_settings.outcome

            # NOTE:
            # When output is set in record settings, use it for recoring result which has
            #   1. Node Input
            #   2. Node Output
            #   3. Node Outcome
            #   4. Node Error

            # INFO:
            result_data = result.model_dump(
                mode="json",  # To avoid serialization errors (like dateatime)
            )

            # TODO_FUTURE: Avoid dulicate data recoding for outcome and input
            outcome_data = result.outcome
            outcome_data = outcome_data.model_dump() if hasattr(outcome_data, "model_dump") else outcome_data

            # Record the node output
            execution_context.artifact_manager.record_data(
                record_type="result",
                data=result_data,
                record_settings=result_record_settings,
                execution_context=execution_context,
            )

            # Record the node outcome
            execution_context.artifact_manager.record_data(
                record_type="outcome",
                data=outcome_data,
                record_settings=outcome_record_settings,
                execution_context=execution_context,
            )

        return None

    async def _continue_after_streaming(self, execution_context: ContextT) -> None:
        """Continue processing remaining nodes after streaming completes"""
        try:
            # Wait for streaming to complete
            current_streaming_context = execution_context.streaming_contexts[execution_context.current_node_identifier]
            execution_context.logger.debug(
                f"_continue_after_streaming: waiting for completion at node {execution_context.current_node_identifier}"
            )
            await current_streaming_context.completion_event.wait()
            execution_context.logger.debug(
                f"_continue_after_streaming: streaming completed for {execution_context.current_node_identifier}"
            )

            if not current_streaming_context.successfull:
                raise current_streaming_context.error or ValueError("Streaming unsuccessful")

            # NOTE: Streaming result are added to execution results inside notify_streaming_complete()
            # -- execution_context.execution_results[execution_context.current_node_identifier] = c_str_context.result
            # Continue with remaining nodes using the same execution strategy
            start_index = execution_context.current_node_index + 1
            if self.flow_definition.execution_strategy == ExecutionStrategyEnum.sequential:
                await self._execute_nodes(execution_context, sequential=True, start_index=start_index)
            else:
                await self._execute_nodes(execution_context, sequential=False, start_index=start_index)

            execution_context.completed_at = datetime.now()
            execution_context.execution_status = ExecutionStatusEnum.COMPLETED
            await self.execution_recorder.update_execution_in_db(execution_context)

        except Exception:
            execution_context.execution_status = ExecutionStatusEnum.FAILED
            execution_context.logger.exception("Post-streaming execution failed")
            await self.execution_recorder.update_execution_in_db(execution_context)
            raise

    def set_node_execution_failed(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        message: str,
    ) -> NodeExecutionResult:
        execution_context.execution_failed = True
        execution_context.execution_failed_message = message

        return NodeExecutionResult(
            executable_type=node_definition.executable_type,
            node_identifier=node_id,
            execution_status=ExecutionStatusEnum.FAILED,
            input=None,
            output=None,
            outcome=None,
            error=message,
            created_at=datetime.now(),
        )
