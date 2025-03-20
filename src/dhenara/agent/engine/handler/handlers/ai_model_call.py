import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from dhenara.agent.dsl.base import ExecutableNodeDefinition, ExecutionContext, StreamingStatusEnum
from dhenara.agent.engine.handler import NodeHandler
from dhenara.agent.types import (
    AIModelCallNodeOutputData,
    FlowNodeExecutionStatusEnum,
    FlowNodeOutput,
    NodeExecutionResult,
    NodeInput,
)

# from common.csource.apps.model_apps.app_ai_connect.libs.tsg.orchestrator import AIModelCallOrchestrator
from dhenara.ai import AIModelClient
from dhenara.ai.types import AIModelCallConfig, AIModelCallResponse
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.api import (
    SSEErrorCode,
    SSEErrorData,
    SSEErrorResponse,
    SSEEventType,
)

logger = logging.getLogger(__name__)


class AIModelCallHandler(NodeHandler):
    def __init__(
        self,
        identifier: str = "ai_model_call_handler",
    ):
        super().__init__(identifier=identifier)
        self.resource_config: ResourceConfig | None = None

    async def handle(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        resource_config: ResourceConfig,
    ) -> Any:
        self.resource_config = resource_config

        if not self.resource_config:
            raise ValueError("resource_config must be set for ai_model_call")

        result = await self._call_ai_model(
            node_definition=node_definition,
            node_input=node_input,
            execution_context=execution_context,
            streaming=False,
        )
        return result

    async def _call_ai_model(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        streaming: bool,
    ) -> NodeExecutionResult[AIModelCallNodeOutputData] | AsyncGenerator:
        user_selected_resource = None
        initial_input = execution_context.get_initial_input()
        selected_resources = initial_input.resources if initial_input and initial_input.resources else []

        if len(selected_resources) == 1:
            user_selected_resource = selected_resources[0]
        else:
            user_selected_resource = next(
                (resource for resource in selected_resources if resource.is_default),
                None,
            )

        if user_selected_resource and not node_definition.check_resource_in_node(user_selected_resource):
            self.set_node_execution_failed(
                node_definition=node_definition,
                execution_context=execution_context,
                message=(
                    f"User selected resouce {user_selected_resource.model_dump_json()} is not available in this node. "
                    "Either provide a valid resource or call with no resources."
                ),
            )
            return None

        if user_selected_resource:
            node_resource = user_selected_resource
        else:
            # Select the default resource
            logger.debug(f"Selecting default resource for node {execution_context.current_node_identifier}.")
            node_resource = next(
                (resource for resource in node_definition.resources if resource.is_default),
                None,
            )

        if not node_resource:
            raise ValueError("No default resource found in flow node configuration")

        logger.debug(f"call_ai_model: node_resource={node_resource}")
        ai_model_ep = self.resource_config.get_resource(node_resource)
        logger.debug(f"call_ai_model: ai_model_ep={ai_model_ep}")

        # Parse inputs
        current_prompt = await self.process_input_contents_and_node_prompt(
            node_definition=node_definition,
            node_input=node_input,
            model=ai_model_ep.ai_model,
        )

        # TODO: Previous prompts
        # if number_of_previous_prompts_to_send > 0:
        #     previous_prompts = conversation_node.get_ancestor_prompts(
        #         number=number_of_previous_prompts_to_send,
        #         dest_model=model_endpoint.ai_model,
        #     )

        node_options = node_definition.ai_settings.get_options() if node_definition.ai_settings else {}
        input_options = node_input.options if node_input and node_input.options else {}

        node_options.update(input_options)

        # pop the non-standard options.  NOTE: pop
        reasoning = node_options.pop("reasoning", True)
        test_mode = node_options.pop("test_mode", False)

        # Get actual model call options
        options = ai_model_ep.ai_model.get_options_with_defaults(node_options)

        # TODO_FUTURE: For image models
        # if functional_type == AIModelFunctionalTypeEnum.IMAGE_GENERATION:
        #    if model_endpoint.ai_model.provider == AIModelProviderEnum.OPEN_AI:
        #        options["response_format"] = "b64_json"

        # Max*tokens are set to None so that model's max value is choosen
        max_output_tokens = options.get("max_output_tokens", 16000)
        if reasoning:
            max_reasoning_tokens = options.get("max_reasoning_tokens", 8000)
        else:
            max_reasoning_tokens = None
        logger.debug(f"call_ai_model: options={options}")

        # Process system instructos
        instructions = []

        # TODO_FUTRE: Add system instructions/appropriate settings to element base
        # if node_definition.system_instructions:
        #    instructions += node_definition.system_instructions

        if node_definition.ai_settings and node_definition.ai_settings.system_instructions:
            instructions += node_definition.ai_settings.system_instructions

        logger.debug(f"call_ai_model: instructions={instructions}")

        # Process previous prompts
        previous_node_outputs_as_prompts: list = await self.get_previous_node_outputs_as_prompts(
            node_definition,
            execution_context,
            ai_model_ep.ai_model,
        )
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
                test_mode=test_mode,
            ),
        )

        response = await client.generate_async(
            prompt=current_prompt,
            context=previous_prompts,
            instructions=instructions,
        )
        if not isinstance(response, AIModelCallResponse):
            logger.exception(
                f"Illegal response type for {type(response)} AIModel Call. Expected type is AIModelCallResponse"
            )

        if streaming:
            if not isinstance(response.stream_generator, AsyncGenerator):
                logger.exception(f"Streaming should return an AsyncGenerator, not {type(response)}")

            # stream_generator = response.stream_generator
            stream_generator = self.generate_stream_response(
                node_definition=node_definition,
                node_input=node_input,
                execution_context=execution_context,
                stream_generator=response.stream_generator,
            )
            execution_context.stream_generator = stream_generator
            return "abc"  # Should retrun a non None value: TODO: Fix this

        # Non streaming
        logger.debug(f"call_ai_model: status={response.status}, response={response},")
        node_output = FlowNodeOutput[AIModelCallNodeOutputData](
            data=AIModelCallNodeOutputData(
                response=response,
            )
        )

        status = (
            FlowNodeExecutionStatusEnum.COMPLETED if response.status.successful else FlowNodeExecutionStatusEnum.FAILED
        )
        result = NodeExecutionResult[AIModelCallNodeOutputData](
            node_identifier=execution_context.current_node_identifier,
            status=status,
            node_input=node_input,
            node_output=node_output,
            # storage_data={},
            created_at=datetime.now(),
        )

        return result

    async def generate_stream_response(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
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

                    node_identifier = execution_context.current_node_identifier
                    node_output = FlowNodeOutput[AIModelCallNodeOutputData](
                        data=AIModelCallNodeOutputData(
                            response=final_response,
                        )
                    )

                    status = (
                        FlowNodeExecutionStatusEnum.COMPLETED
                        if final_response.status.successful
                        else FlowNodeExecutionStatusEnum.FAILED
                    )
                    result = NodeExecutionResult[AIModelCallNodeOutputData](
                        node_identifier=node_identifier,
                        status=status,
                        node_input=node_input,
                        node_output=node_output,
                        # storage_data=storage_data,
                        created_at=datetime.now(),
                    )

                    # NOTE: `await`
                    await execution_context.notify_streaming_complete(
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


class AIModelCallStreamHandler(AIModelCallHandler):
    def __init__(
        self,
    ):
        super().__init__(identifier="ai_model_call_stream_handler")

    async def handle(
        self,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        resource_config: ResourceConfig,
    ) -> Any:
        self.resource_config = resource_config

        if not self.resource_config:
            raise ValueError("resource_config must be set for ai_model_call")

        result = await self._call_ai_model(
            node_definition=node_definition,
            node_input=node_input,
            execution_context=execution_context,
            streaming=True,
        )
        return result
