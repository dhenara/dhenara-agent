# Copyright 2024-2025 Dhenara Inc. All rights reserved.
# flow_orchestrator.py
#  from tenacity import retry, stop_after_attempt, wait_exponential : TODO Future
import asyncio
import logging
from asyncio import Event, create_task
from collections.abc import AsyncGenerator
from typing import Any

from dhenara.agent.types import (
    AIModelCallNodeOutputData,
    ExecutionStrategyEnum,
    FlowContext,
    FlowDefinition,
    FlowExecutionStatusEnum,
    FlowNode,
    FlowNodeExecutionResult,
    FlowNodeExecutionStatusEnum,
    FlowNodeOutput,
    FlowNodeTypeEnum,
    Resource,
    SpecialNodeIdEnum,
    StreamingContext,
    StreamingStatusEnum,
    UserInput,
)

# from common.csource.apps.model_apps.app_ai_connect.libs.tsg.orchestrator import AIModelCallOrchestrator
from dhenara.ai import AIModelClient
from dhenara.ai.providers.common import PromptFormatter
from dhenara.ai.types import (
    AIModel,
    AIModelCallConfig,
    AIModelCallResponse,
    ResourceConfig,
)
from dhenara.ai.types.shared.api import (
    SSEErrorCode,
    SSEErrorData,
    SSEErrorResponse,
    SSEEventType,
)
from django.utils import timezone

from common.csource.glb.exceptions import ApiValidationError

from .execution_recorder import ExecutionRecorder

logger = logging.getLogger(__name__)


class FlowOrchestrator:
    def __init__(
        self,
        flow_definition: FlowDefinition,
        resource_config:ResourceConfig,
    ):
        self.flow_definition = flow_definition
        self.execution_recorder = None
        self.resource_config = resource_config

        self._node_handlers = {
            FlowNodeTypeEnum.ai_model_call: self._handle_ai_model_call,
            FlowNodeTypeEnum.ai_model_call_stream: self._handle_ai_model_call_stream,
            FlowNodeTypeEnum.rag_index: self._handle_rag_index,
            FlowNodeTypeEnum.rag_query: self._handle_rag_query,
        }

    def get_node_execution_handler(self, flow_node_type: FlowNodeTypeEnum):
        handler = self._node_handlers.get(flow_node_type)
        if not handler:
            raise ValueError(f"Unsupported flow_node type: {flow_node_type}")

        return handler

    async def execute(self, context: FlowContext) -> dict[str, FlowNodeExecutionResult] | AIModelCallResponse:
        """Execute the flow with streaming support"""

        try:
            context.execution_status = FlowExecutionStatusEnum.RUNNING
            self.execution_recorder = ExecutionRecorder()
            await self.execution_recorder.update_execution_in_db(context, create=True)

            if self.flow_definition.execution_strategy == ExecutionStrategyEnum.sequential:
                result = await self._execute_sequential(context)

                # if self.has_any_streaming_node():
                # if isinstance(result, AsyncGenerator):
                if isinstance(result, AIModelCallResponse) and result.stream_generator and isinstance(result.stream_generator, AsyncGenerator):
                    background_tasks = set()

                    # Create a background task to continue processing after streaming
                    task = create_task(self._continue_after_streaming(context))
                    context.execution_status = FlowExecutionStatusEnum.PENDING

                    # NOTE: Below 2 lines are from RUFF:RUF006
                    # https://docs.astral.sh/ruff/rules/asyncio-dangling-task/
                    # Add task to the set. This creates a strong reference.
                    background_tasks.add(task)

                    # To prevent keeping references to finished tasks forever,
                    # make each task remove its own reference from the set after completion:
                    task.add_done_callback(background_tasks.discard)

                    return result

            elif self.flow_definition.execution_strategy == ExecutionStrategyEnum.parallel:
                # TODO: Missing fns
                result = await self._execute_parallel(context)

            else:
                raise NotImplementedError(f"Unsupported execution strategy: {self.flow_definition.execution_strategy}")
            context.execution_status = FlowExecutionStatusEnum.COMPLETED
            logger.debug(f"execute: Execution completed. execution_results={context.execution_results}")

            await self.execution_recorder.update_execution_in_db(context)
            logger.debug("execute: Finished updating DB")
            return context.execution_results

        except Exception:
            context.execution_status = FlowExecutionStatusEnum.FAILED
            logger.exception("Flow execution failed")
            raise

    async def _execute_sequential(self, context: FlowContext) -> AsyncGenerator | dict[str, FlowNodeExecutionResult]:
        """Execute nodes sequentially"""
        return await self._execute_nodes(context, sequential=True)

    async def _execute_parallel(self, context: FlowContext) -> dict[str, FlowNodeExecutionResult]:
        """Execute nodes in parallel"""
        return await self._execute_nodes(context, sequential=False)

    async def _execute_nodes(
        self,
        context: FlowContext,
        sequential: bool,
        start_index: int = 0,
    ) -> AsyncGenerator | dict[str, FlowNodeExecutionResult]:
        """Core execution logic for both sequential and parallel node processing"""
        nodes_to_process = self.flow_definition.nodes[start_index:]

        if sequential:
            for index, flow_node in enumerate(nodes_to_process, start=start_index):
                result = await self._process_single_node(flow_node, context, index)

                if result is not None:  # Streaming case will return an async generator
                    return result

                if context.execution_failed:
                    context.execution_status = FlowExecutionStatusEnum.FAILED
                    return None

        else:
            # Parallel execution
            tasks = [
                create_task(
                    self._process_single_node(
                        flow_node,
                        context,
                        index,
                    )
                )
                for index, flow_node in enumerate(nodes_to_process, start=start_index)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions from parallel execution
            for result in results:
                if isinstance(result, Exception):
                    context.execution_status = FlowExecutionStatusEnum.FAILED
                    raise result
                if context.execution_failed:
                    context.execution_status = FlowExecutionStatusEnum.FAILED
                    return None

        # Execution completed
        context.completed_at = timezone.now()
        return context.execution_results

    async def _process_single_node(
        self,
        flow_node: FlowNode,
        context: FlowContext,
        index: int,
    ) -> AsyncGenerator | None:
        """Process a single node and handle its result"""
        context.set_current_node(index)
        handler = self.get_node_execution_handler(flow_node.type)

        if flow_node.is_streaming():
            # Handle streaming nodes
            context.streaming_contexts[flow_node.identifier] = StreamingContext(
                status=StreamingStatusEnum.STREAMING,
                completion_event=Event(),
            )
            context.current_node_index = index
            # Execute streaming node and return generator
            result = await handler(flow_node, context)
            return result

        # Execute non-streaming node
        result = await handler(flow_node, context)
        return await self._process_single_node_completion(flow_node=flow_node, context=context, result=result)

    async def _process_single_node_completion(
        self,
        flow_node: FlowNode,
        context: FlowContext,
        result,
    ) -> AsyncGenerator | None:
        context.execution_results[context.current_node_identifier] = result
        context.updated_at = timezone.now()

        """ TODO
        # Determine if we should send SSE update
        should_send_update = flow_node.response_settings and flow_node.response_settings.send_updates

        if should_send_update:
            if self.response_protocol == ResponseProtocolEnum.HTTP_SSE:
                return self._create_node_execution_sse_generator(result)
            else:
                raise ValueError()
        """

        return None

    async def _continue_after_streaming(self, context: FlowContext) -> None:
        """Continue processing remaining nodes after streaming completes"""
        try:
            # Wait for streaming to complete
            current_streaming_context = context.streaming_contexts[context.current_node_identifier]
            logger.debug(f"_continue_after_streaming: waiting for completion at node {context.current_node_identifier}")
            await current_streaming_context.completion_event.wait()
            logger.debug(f"_continue_after_streaming: streaming completed for {context.current_node_identifier}")

            if not current_streaming_context.successfull:
                raise current_streaming_context.error or ValueError("Streaming unsuccessful")

            # NOTE: Streaming result are added to execution results inside notify_streaming_complete()
            # -- context.execution_results[context.current_node_identifier] = current_streaming_context.result
            # Continue with remaining nodes using the same execution strategy
            start_index = context.current_node_index + 1
            if self.flow_definition.execution_strategy == ExecutionStrategyEnum.sequential:
                await self._execute_nodes(context, sequential=True, start_index=start_index)
            else:
                await self._execute_nodes(context, sequential=False, start_index=start_index)

            context.completed_at = timezone.now()
            context.execution_status = FlowExecutionStatusEnum.COMPLETED
            await self.execution_recorder.update_execution_in_db(context)

        except Exception:
            context.execution_status = FlowExecutionStatusEnum.FAILED
            logger.exception("Post-streaming execution failed")
            await self.execution_recorder.update_execution_in_db(context)
            raise

    # FlowNode handler implementations
    async def _handle_ai_model_call(self, flow_node: FlowNode, context: FlowContext) -> FlowNodeExecutionResult[AIModelCallNodeOutputData]:
        result = await self._call_ai_model(flow_node, context, streaming=False)
        return result

    async def _handle_ai_model_call_stream(self, flow_node: FlowNode, context: FlowContext) -> AsyncGenerator[Any, None]:
        result = await self._call_ai_model(flow_node, context, streaming=True)
        return result

    async def _handle_rag_index(self, flow_node: FlowNode, context: FlowContext) -> Any:
        # Implement RAG indexing
        raise NotImplementedError()

    async def _handle_rag_query(self, flow_node: FlowNode, context: FlowContext) -> Any:
        # Implement RAG querying
        raise NotImplementedError()

    async def _call_ai_model(
        self,
        flow_node: FlowNode,
        context: FlowContext,
        streaming: bool,
    ) -> FlowNodeExecutionResult[AIModelCallNodeOutputData] | AsyncGenerator:
        user_selected_resource = None
        selected_resources = self.get_user_selected_resources(flow_node, context)
        if len(selected_resources) == 1:
            user_selected_resource = selected_resources[0]
        else:
            user_selected_resource = next((resource for resource in selected_resources if resource.is_default), None)

        if user_selected_resource and not flow_node.check_resource_in_node(user_selected_resource):
            self.set_node_execution_failed(
                flow_node=flow_node,
                context=context,
                message=f"User selected resouce {user_selected_resource.model_dump_json()} is not available in this node. Either provide a valid resource or call with no resources.",
            )
            return None

        if user_selected_resource:
            node_resource = user_selected_resource
        else:
            # Select the default resource
            logger.debug(f"Selecting default resource for node {flow_node.identifier}.")
            node_resource = next((resource for resource in flow_node.resources if resource.is_default), None)

        if not node_resource:
            raise ValueError("No default resource found in flow node configuration")

        logger.debug(f"call_ai_model: node_resource={node_resource}")
        ai_model_ep = self.resource_config.get_resource (node_resource)
        logger.debug(f"call_ai_model: ai_model_ep={ai_model_ep}")

        # Parse inputs
        user_inputs: list[UserInput] = self.get_user_inputs(flow_node, context)
        current_prompt = await self.process_user_inputs_and_node_prompt(flow_node, user_inputs, ai_model_ep.ai_model)

        # Process options
        options = flow_node.ai_settings.get_options()
        for user_input in user_inputs:
            options.update(user_input.options)

        reasoning = options.get("reasoning", True)
        max_output_tokens = options.get("max_output_tokens", 16000)
        max_reasoning_tokens = options.get("max_reasoning_tokens", 8000)
        logger.debug(f"call_ai_model: options={options}")

        # Process system instructos
        instructions = []
        if context.flow_definition.system_instructions:
            instructions += context.flow_definition.system_instructions

        if flow_node.ai_settings.system_instructions:
            instructions += flow_node.ai_settings.system_instructions

        logger.debug(f"call_ai_model: instructions={instructions}")

        # Process previous prompts
        previous_node_outputs_as_prompts: list = await self.get_previous_node_outputs_as_prompts(flow_node, context, ai_model_ep.ai_model)
        # logger.debug(f"call_ai_model:  previous_node_output_prompt={previous_node_outputs_as_prompts}")

        previous_prompts_from_conversaion = []  # TODO:
        previous_prompts = previous_prompts_from_conversaion + previous_node_outputs_as_prompts
        logger.debug(f"call_ai_model: current_prompt = {current_prompt}, previous_prompts={previous_prompts}")

        user_id = "usr_id_abcd"  # TODO

        client = AIModelClient(
            is_async=True,
            model_endpoint=ai_model_ep,
            config=AIModelCallConfig(
                streaming=streaming,
                max_output_tokens=max_output_tokens,
                reasoning=reasoning,
                max_reasoning_tokens=max_reasoning_tokens,
                options={},  # TODO
                metadata={"user_id": user_id},
                test_mode=False,
            ),
        )

        response = await client.generate_async(
            prompt=current_prompt,
            context=previous_prompts,
            instructions=instructions,
        )
        if not isinstance(response, AIModelCallResponse):
            logger.exception(f"Illegal response type for {type(response)} AIModel Call. Expected type is AIModelCallResponse")

        if streaming:
            if not isinstance(response.stream_generator, AsyncGenerator):
                logger.exception(f"Streaming should return an AsyncGenerator, not {type(response)}")

            # stream_generator = response.stream_generator
            stream_generator = self.generate_stream_response(flow_node=flow_node, context=context, stream_generator=response.stream_generator)
            context.stream_generator = stream_generator
            return "abc"  # Should retrun a non None value: TODO: Fix this

        # Non streaming
        logger.debug(f"call_ai_model: status={response.status}, response={response},")
        node_output = FlowNodeOutput[AIModelCallNodeOutputData](
            data=AIModelCallNodeOutputData(
                response=response,
            )
        )

        status = FlowNodeExecutionStatusEnum.COMPLETED if response.status.successful else FlowNodeExecutionStatusEnum.FAILED
        storage_data = {}  # TODO
        result = FlowNodeExecutionResult[AIModelCallNodeOutputData](
            node_identifier=flow_node.identifier,
            status=status,
            user_inputs=user_inputs,
            node_output=node_output,
            storage_data=storage_data,
            created_at=timezone.now(),
        )

        return result

    async def generate_stream_response(
        self,
        flow_node: FlowNode,
        context: FlowContext,
        stream_generator: AsyncGenerator,
    ):
        if not stream_generator:
            raise ValueError("No streaming response available")

        try:
            # Note:
            # response_stream_generator is of type  AsyncGenerator[tuple[StreamingChatResponse, ChatResponse | None]]
            async for chunk, final_response in stream_generator:
                if chunk and chunk.event == SSEEventType.ERROR:
                    logger.error(f"Stream Error: {chunk}")
                    yield chunk

                if chunk and chunk.event == SSEEventType.TOKEN_STREAM:
                    yield chunk

                if final_response:
                    logger.debug(f"Final streaming response: {final_response}")
                    if not isinstance(final_response, AIModelCallResponse):
                        logger.fatal(f"Final streaming response type {type(final_response)} is not AIModelCallResponse")

                    node_identifier = flow_node.identifier
                    node_output = FlowNodeOutput[AIModelCallNodeOutputData](
                        data=AIModelCallNodeOutputData(
                            response=final_response,
                        )
                    )

                    status = FlowNodeExecutionStatusEnum.COMPLETED if final_response.status.successful else FlowNodeExecutionStatusEnum.FAILED
                    storage_data = {}  # TODO
                    result = FlowNodeExecutionResult[AIModelCallNodeOutputData](
                        node_identifier=node_identifier,
                        status=status,
                        user_inputs=None,
                        node_output=node_output,
                        storage_data=storage_data,
                        created_at=timezone.now(),
                    )

                    # NOTE: `await`
                    await context.notify_streaming_complete(
                        identifier=node_identifier,
                        streaming_status=StreamingStatusEnum.COMPLETED,
                        result=result,
                    )
                    return  # Stop the generator

        except Exception as e:
            logger.exception(f"Error in stream generation: {e}")
            yield self.generate_sse_error(f"Stream processing error: {e}")
            return  # Stop the generator

    def generate_sse_error(self, message: str | Exception):
        return SSEErrorResponse(
            data=SSEErrorData(
                error_code=SSEErrorCode.server_error,
                message=str(message),
                details=None,
            )
        )

    def get_user_selected_resources(self, flow_node: FlowNode, context: FlowContext) -> list[Resource]:
        user_input_sources = flow_node.input_settings.input_source.user_input_sources
        resources = []
        for input_source in user_input_sources:
            if input_source == SpecialNodeIdEnum.FULL:
                resources = context.initial_input.resources
            else:
                raise ApiValidationError(f"user_input_source={input_source} not supported for resurce selection. Only 'full' is supported now")
        return resources

    def get_user_inputs(self, flow_node: FlowNode, context: FlowContext) -> list[UserInput]:
        user_input_sources = flow_node.input_settings.input_source.user_input_sources
        user_inputs = []
        for input_source in user_input_sources:
            if input_source == SpecialNodeIdEnum.FULL:
                user_inputs.append(context.initial_input.user_input)
            else:
                raise ApiValidationError(f"user_input_source={input_source} not supported for input selection. Only 'full' is supported now")

        return user_inputs

    def set_node_execution_failed(self, flow_node: FlowNode, context: FlowContext, message):
        context.execution_failed = True
        context.execution_failed_message = message

    async def process_user_inputs_and_node_prompt(
        self,
        flow_node: FlowNode,
        user_inputs: list[UserInput],
        model: AIModel,
    ) -> list[dict]:
        user_input_content = " ".join([await user_input.get_content() for user_input in user_inputs])
        logger.debug(f"call_ai_model: user_input_content={user_input_content}")

        # If
        node_prompt = flow_node.ai_settings.node_prompt
        has_full_node_prompt = node_prompt and node_prompt.prompt

        if user_inputs and has_full_node_prompt:
            raise ApiValidationError(
                f"Illegal input settings for node {flow_node.identifier}. Conflicting `node_prompt` and `user_inputs` settings. \
                Eventhhogh this is taken care in node validation fn `validate_input_settings`, somethhing got messed up."
            )

        if has_full_node_prompt:
            final_content = node_prompt.get_full_prompt(user_prompt=user_input_content)
        else:
            if node_prompt:  # Process to add `pre` and `post` prompts
                final_content = node_prompt.get_full_prompt(user_prompt=user_input_content)
            else:
                final_content = user_input_content

        prompts = PromptFormatter.format_conversion_node_as_prompts(
            model=model,
            user_query=final_content,
            attached_files=[],
            previous_response=None,
            max_words_query=None,
            max_words_files=None,
            max_words_response=None,
        )
        return prompts[0]

    async def get_previous_node_outputs_as_prompts(
        self,
        flow_node: FlowNode,
        context: FlowContext,
        model: AIModel,
    ) -> list:
        node_output_sources = flow_node.input_settings.input_source.node_output_sources
        outputs_as_prompts = []
        try:
            for source_node_identifier in node_output_sources:
                if source_node_identifier == SpecialNodeIdEnum.PREVIOUS:
                    previous_node_identifier = context.flow_definition.get_previous_node_identifier(flow_node.identifier)
                    previous_node_execution_result = context.execution_results.get(previous_node_identifier)
                else:
                    previous_node_execution_result = context.execution_results.get(source_node_identifier)

                previous_node_output = previous_node_execution_result.node_output.data

                # TODO: Check if node is saved to DB as ConversationNode and , and get it from that
                # For now processing execution results text contents

                prevnode_userinput = previous_node_execution_result.user_inputs[0]
                if prevnode_userinput:
                    question = prevnode_userinput.primary_content
                else:
                    question = None

                prompts = PromptFormatter.format_conversion_node_as_prompts(
                    model=model,
                    user_query=question,
                    attached_files=[],  # TODO: Get from user inputs
                    previous_response=previous_node_output.response.full_response,
                    max_words_query=None,
                    max_words_files=None,
                    max_words_response=None,
                )

                outputs_as_prompts += prompts

        except Exception as e:
            raise ApiValidationError(f"previous_node_output: Error: {e}")

        return outputs_as_prompts

    '''TODO
    def _create_node_execution_sse_generator(self, result: FlowNodeExecutionResult) -> AsyncGenerator:
        """Create an SSE generator for node execution results"""
        async def generator():
            try:
                sse_response = SSENodeExecutionResultResponse(
                    event="node_execution_result",
                    data={
                        "node_identifier": result.node_identifier,
                        "status": result.status,
                        "user_inputs": [input.model_dump() for input in result.user_inputs] if result.user_inputs else None,
                        "node_output": result.node_output.model_dump() if result.node_output else None,
                        "storage_data": result.storage_data,
                        "created_at": result.created_at.isoformat(),
                    },
                )
                yield sse_response

            except Exception as e:
                logger.exception("Error generating SSE response")
                error_response = SSEErrorResponse(
                    data=SSEErrorData(
                        error_code=SSEErrorCode.server_error,
                        message="Error generating node execution result",
                        details={"error": str(e)},
                    ),
                )
                yield error_response

        return generator()


    def _create_final_response(self, context: FlowContext) -> dict[str, Any] | AsyncGenerator:
        """Create final response based on protocol"""
        if self._final_protocol == ResponseProtocolEnum.HTTP:
            return self._create_final_http_response(context)
        else:
            return self._create_final_sse_response(context)

    def _create_final_http_response(self, context: FlowContext) -> dict[str, Any]:
        """Create final HTTP response with all results"""
        return {
            "status": context.execution_status,
            "results": {
                node_id: result.model_dump()
                for node_id, result in context.execution_results.items()
                if (
                    self.flow_definition.nodes[context.get_node_index(node_id)]
                    .response_settings.include_in_final
                )
            },
            "completed_at": context.completed_at.isoformat(),
        }

    def _create_final_sse_response(self, context: FlowContext) -> AsyncGenerator:
        """Create final SSE response"""
        async def generator():
            # Send individual results
            for node_id, result in context.execution_results.items():
                if (
                    self.flow_definition.nodes[context.get_node_index(node_id)]
                    .response_settings.include_in_final
                ):
                    yield SSENodeExecutionResultResponse(
                        event="node_result",
                        data=result.model_dump(),
                    )

            # Send final completion message
            yield SSENodeExecutionResultResponse(
                event="flow_complete",
                data={
                    "status": context.execution_status,
                    "completed_at": context.completed_at.isoformat(),
                },
            )

        return generator()
    '''
