import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from dhenara.agent.dsl.base import (
    ExecutableNodeDefinition,
    ExecutionContext,
    ExecutionStatusEnum,
    NodeExecutionResult,
    NodeID,
    NodeInput,
    NodeOutCome,
    NodeOutput,
    SpecialNodeIDEnum,
    StreamingStatusEnum,
)
from dhenara.agent.dsl.flow import FlowNodeExecutor
from dhenara.agent.dsl.inbuilt.flow_nodes.ai_model import (
    AIModelNodeInput,
    AIModelNodeOutcomeData,
    AIModelNodeOutputData,
    AIModelNodeSettings,
)
from dhenara.ai import AIModelClient
from dhenara.ai.types import (
    AIModelCallConfig,
    AIModelCallResponse,
)
from dhenara.ai.types.genai.dhenara.request import Prompt, SystemInstruction
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.api import (
    SSEErrorCode,
    SSEErrorData,
    SSEErrorResponse,
    SSEEventType,
)
from dhenara.ai.types.shared.platform import DhenaraAPIError

logger = logging.getLogger(__name__)


class AIModelNodeExecutor(FlowNodeExecutor):
    input_model = AIModelNodeInput
    setting_model = AIModelNodeSettings

    def __init__(
        self,
        identifier: str = "ai_model_call_handler",
    ):
        super().__init__(identifier=identifier)
        self.resource_config: ResourceConfig | None = None

    async def get_live_input(self) -> AIModelNodeInput:
        # TODO:
        return AIModelNodeInput(
            prompt_variables={
                "requested_plan": "A nextjs project that implements a developer dashboard",
            },
            instruction_variables={},
        )

    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        node_input: NodeInput,
        resource_config: ResourceConfig,
    ) -> Any:
        self.resource_config = resource_config

        if not self.resource_config:
            raise ValueError("resource_config must be set for ai_model_call")

        result = await self._call_ai_model(
            node_id=node_id,
            node_definition=node_definition,
            node_input=node_input,
            execution_context=execution_context,
            streaming=False,
        )
        return result

    async def _call_ai_model(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        streaming: bool,
    ) -> bool | AsyncGenerator:
        # initial_input = execution_context.get_initial_input()
        initial_input = None  # TODO
        node_input = node_input if node_input is not None else initial_input
        if node_input is None:
            raise ValueError("Failed to get inputs for node ")

        # 1. Fix node resource
        # -------------------
        user_selected_resource = None
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

        # 2. Fix Setting
        # -------------------
        settings: AIModelNodeSettings = node_definition.select_settings(node_input=node_input)
        if settings is None or not isinstance(settings, AIModelNodeSettings):
            raise ValueError(f"Invalid setting for node. selected settings is: {settings}")

        # 3. Fix AI Model endpoint
        # -------------------
        logger.debug(f"call_ai_model: node_resource={node_resource}")
        ai_model_ep = self.resource_config.get_resource(node_resource)
        logger.debug(f"call_ai_model: ai_model_ep={ai_model_ep}")

        # 4. Fix Prompt and system instruction
        # -------------------
        # Parse inputs
        prompt = settings.prompt
        instructions = settings.system_instructions

        # Prompt
        if not isinstance(prompt, Prompt):
            raise ValueError(f"Failed to get node prompt. Type is {type(prompt)}")

        prompt.variables.update(node_input.prompt_variables)

        if instructions is not None:
            for instruction in instructions:
                if isinstance(instruction, SystemInstruction):
                    instruction.variables.update(node_input.instruction_variables)
                elif isinstance(instruction, str):
                    pass
                else:
                    raise ValueError(
                        f"Failed to get node prompt. Illegal type of {type(instruction)} in Node instructions"
                    )

        # 5. Fix contex
        # -------------------
        if settings.context:
            context = settings.context
        else:
            previous_node_prompts: list = await self.get_previous_node_outputs_as_prompts(
                node_definition,
                execution_context,
            )
            # logger.debug(f"call_ai_model: previous_prompts={previous_prompts}")
            context = previous_node_prompts

        # 6. Fix options
        # -------------------
        node_options = settings.model_call_config.options if settings.model_call_config else {}

        logger.debug(f"call_ai_model:  prompt={prompt}, context={context} instructions={instructions}")
        logger.debug(f"call_ai_model:  node_optons={node_options}")

        # pop the non-standard options.  NOTE: pop
        reasoning = node_options.pop("reasoning", False)
        test_mode = node_options.pop("test_mode", False)

        # Get actual model call options
        options = ai_model_ep.ai_model.get_options_with_defaults(node_options)

        # Max*tokens are set to None so that model's max value is choosen
        max_output_tokens = options.get("max_output_tokens", 16000)
        if reasoning:
            max_reasoning_tokens = options.get("max_reasoning_tokens", 8000)
        else:
            max_reasoning_tokens = None
        logger.debug(f"call_ai_model: options={options}")

        # 7. AIModelCallConfig
        model_call_config = None
        # -------------------
        if settings.model_call_config:
            model_call_config = settings.model_call_config
            model_call_config.options = options  # Override the refined options
        else:
            user_id = "usr_id_abcd"  # TODO
            model_call_config = AIModelCallConfig(
                streaming=streaming,
                max_output_tokens=max_output_tokens,
                reasoning=reasoning,
                max_reasoning_tokens=max_reasoning_tokens,
                options=options,
                metadata={"user_id": user_id},
                test_mode=test_mode,
            )

        # 8. Call model
        # -------------------
        client = AIModelClient(
            is_async=True,
            model_endpoint=ai_model_ep,
            config=model_call_config,
        )

        response = await client.generate_async(
            prompt=prompt,
            context=context,
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
        node_output = NodeOutput[AIModelNodeOutputData](
            data=AIModelNodeOutputData(
                response=response,
            )
        )

        # Fill output and outcome in execution context
        text_outcome = None
        structured_outcome = None

        if model_call_config.structured_output is not None:
            structured_outcome = response.chat_response.structured()
            if not structured_outcome:
                logger.error("AIModelNode structured_outcome is None when node settings sets structured_output")
        else:
            text_outcome = response.chat_response.text()

        node_outcome = NodeOutCome[AIModelNodeOutcomeData](
            data=AIModelNodeOutcomeData(
                text=text_outcome,
                structured=structured_outcome,
            )
        )

        status = ExecutionStatusEnum.COMPLETED if response.status.successful else ExecutionStatusEnum.FAILED
        result = NodeExecutionResult[AIModelNodeOutputData, AIModelNodeOutcomeData](
            node_identifier=execution_context.current_node_identifier,
            status=status,
            node_input=node_input,
            node_output=node_output,
            node_outcome=node_outcome,
            created_at=datetime.now(),
        )

        execution_context.execution_results[node_id] = result
        execution_context.updated_at = datetime.now()

        return True

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
                    node_output = NodeOutput[AIModelNodeOutputData](
                        data=AIModelNodeOutputData(
                            response=final_response,
                        )
                    )

                    status = (
                        ExecutionStatusEnum.COMPLETED
                        if final_response.status.successful
                        else ExecutionStatusEnum.FAILED
                    )
                    result = NodeExecutionResult[AIModelNodeOutputData, AIModelNodeOutcomeData](
                        node_identifier=node_identifier,
                        status=status,
                        node_input=node_input,
                        node_output=node_output,  # TODO: outcome
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

    async def get_previous_node_outputs_as_prompts(
        self,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
    ) -> list:
        context_sources = node_definition.settings.context_sources if node_definition.settings else []
        outputs_as_prompts = []
        try:
            for source_node_identifier in context_sources:
                if source_node_identifier == SpecialNodeIDEnum.PREVIOUS:
                    previous_node_identifier = execution_context.flow_definition.get_previous_node_identifier(
                        execution_context.current_node_identifier,
                    )
                    previous_node_execution_result = execution_context.execution_results.get(previous_node_identifier)
                else:
                    previous_node_execution_result = execution_context.execution_results.get(source_node_identifier)

                previous_node_output = previous_node_execution_result.node_output.data

                prompt = previous_node_output.response.to_prompt()

                outputs_as_prompts.append(prompt)

        except Exception as e:
            raise DhenaraAPIError(f"previous_node_output: Error: {e}")

        return outputs_as_prompts


class AIModelNodeStreamExecutor(AIModelNodeExecutor):
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
