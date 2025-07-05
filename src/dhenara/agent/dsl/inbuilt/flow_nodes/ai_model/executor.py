import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from dhenara.agent.dsl.base import (
    DADTemplateEngine,
    ExecutableNodeDefinition,
    ExecutionContext,
    ExecutionStatusEnum,
    NodeID,
    NodeInput,
    NodeOutput,
    RecordFileFormatEnum,
    RecordSettingsItem,
    SpecialNodeIDEnum,
    StreamingStatusEnum,
)
from dhenara.agent.dsl.components.flow import FlowNodeExecutionResult, FlowNodeExecutor
from dhenara.agent.dsl.inbuilt.flow_nodes.ai_model import (
    AIModelNodeInput,
    AIModelNodeOutcome,
    AIModelNodeOutput,
    AIModelNodeOutputData,
    AIModelNodeSettings,
)
from dhenara.agent.dsl.inbuilt.flow_nodes.defs import FlowNodeTypeEnum
from dhenara.agent.observability.tracing import trace_node
from dhenara.agent.observability.tracing.data import add_trace_attribute, trace_collect
from dhenara.ai import AIModelClient
from dhenara.ai.types import (
    AIModelCallConfig,
    AIModelCallResponse,
    ImageContentFormat,
)
from dhenara.ai.types.genai.dhenara.request import Prompt, SystemInstruction
from dhenara.ai.types.resource import ResourceConfig
from dhenara.ai.types.shared.api import (
    SSEErrorCode,
    SSEErrorData,
    SSEErrorResponse,
    SSEEventType,
)
from dhenara.ai.types.shared.file import StoredFile
from dhenara.ai.types.shared.platform import DhenaraAPIError

from .tracing import (
    ai_model_api_provider_attr,
    ai_model_name_attr,
    ai_model_node_tracing_profile,
    ai_model_provider_attr,
    api_call_started_attr,
    charge_attr,
    context_count_attr,
    cost_attr,
    final_prompt_attr,
    model_call_config_attr,
    model_options_attr,
    node_resource_query_attr,
    node_resource_type_attr,
    prompt_context_0_attr,
    prompt_context_1_attr,
    prompt_context_2_attr,
    system_instructions_attr,
    test_mode_attr,
)

logger = logging.getLogger(__name__)


class AIModelNodeExecutionResult(FlowNodeExecutionResult[AIModelNodeInput, AIModelNodeOutput, AIModelNodeOutcome]):
    pass


class AIModelNodeExecutor(FlowNodeExecutor):
    node_type = FlowNodeTypeEnum.ai_model_call.value
    input_model = AIModelNodeInput
    setting_model = AIModelNodeSettings
    _tracing_profile = ai_model_node_tracing_profile

    def get_result_class(self):
        return AIModelNodeExecutionResult

    @trace_node(FlowNodeTypeEnum.ai_model_call.value)
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
    ) -> AIModelNodeExecutionResult:
        if not execution_context.resource_config:
            raise ValueError("resource_config must be set for ai_model_call")

        result = await self._call_ai_model(
            node_id=node_id,
            node_definition=node_definition,
            node_input=node_input,
            execution_context=execution_context,
            streaming=False,
        )
        return result

    @trace_collect()
    async def _call_ai_model(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        node_input: NodeInput,
        execution_context: ExecutionContext,
        streaming: bool,
    ) -> bool | AsyncGenerator:
        # 1. Fix node resource
        # -------------------
        user_selected_resource = None
        resources_override = (
            node_input.settings_override.resources
            if node_input and node_input.settings_override and node_input.settings_override.resources
            else []
        )

        if len(resources_override) == 1:
            user_selected_resource = resources_override[0]
        else:
            user_selected_resource = next(
                (resource for resource in resources_override if resource.is_default),
                None,
            )

        if user_selected_resource and not node_definition.check_resource_in_node(user_selected_resource):
            return self.set_node_execution_failed(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
                message=(
                    f"User selected resouce {user_selected_resource.model_dump_json()} is not available in this node. "
                    "Either provide a valid resource or call with no resources."
                ),
            )

        if user_selected_resource:
            node_resource = user_selected_resource
        else:
            # Select the default resource
            logger.debug(f"Selecting default resource for node {execution_context.current_node_identifier}.")
            node_resource = next(
                (resource for resource in node_definition.settings.resources if resource.is_default),
                None,
            )

        if not node_resource:
            raise ValueError("No default resource found in flow node configuration")

        add_trace_attribute(
            node_resource_type_attr,
            getattr(node_resource, "item_type", "unknown"),
        )
        # Add query information if available
        if hasattr(node_resource, "query"):
            add_trace_attribute(node_resource_query_attr, node_resource.query)

        # 2. Fix Setting
        # -------------------
        settings: AIModelNodeSettings = node_definition.select_settings(node_input=node_input)
        if settings is None or not isinstance(settings, AIModelNodeSettings):
            raise ValueError(f"Invalid setting for node. selected settings is: {settings}")

        # 3. Fix AI Model endpoint
        # -------------------
        ai_model_ep = execution_context.resource_config.get_resource(node_resource)
        add_trace_attribute(ai_model_name_attr, ai_model_ep.ai_model.model_name)
        add_trace_attribute(ai_model_provider_attr, ai_model_ep.ai_model.provider)
        add_trace_attribute(ai_model_api_provider_attr, ai_model_ep.api.provider)

        # 4. Fix Prompt and system instruction
        # -------------------
        prompt = settings.prompt
        instructions = settings.system_instructions

        # Prompt
        if not isinstance(prompt, Prompt):
            raise ValueError(f"Failed to get node prompt. Type is {type(prompt)}")

        if node_input:
            prompt.variables.update(node_input.prompt_variables)

        prompt = DADTemplateEngine.render_dad_template(
            template=prompt,
            variables=prompt.variables,
            execution_context=execution_context,
        )

        # Add the final prompt to tracing
        add_trace_attribute(
            final_prompt_attr,
            prompt.text if hasattr(prompt, "text") else str(prompt),
        )

        # TODO_FUTURE: template support for instructions and context?
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

        # Add system instructions to tracing
        add_trace_attribute(system_instructions_attr, instructions)

        # 5. Fix context
        # -------------------
        if settings.context:
            context = settings.context
        else:
            previous_node_prompts = await self.get_previous_node_outputs_as_prompts(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
            )
            context = previous_node_prompts

        # Add context to tracing
        if context:
            add_trace_attribute(context_count_attr, len(context))
            # Add preview of first few context items
            for i, ctx in enumerate(context[:3]):
                attr = prompt_context_0_attr if i == 0 else prompt_context_1_attr if i == 1 else prompt_context_2_attr
                add_trace_attribute(
                    attr,
                    ctx.text if hasattr(ctx, "text") else str(ctx),
                )

        # 6. Fix options
        # -------------------
        node_options = settings.model_call_config.options if settings.model_call_config else {}

        # logger.debug(f"call_ai_model:  prompt={prompt}, context={context} instructions={instructions}")
        # logger.debug(f"call_ai_model:  node_optons={node_options}")

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

        # Add options to tracing
        add_trace_attribute(model_options_attr, options)
        add_trace_attribute(test_mode_attr, test_mode)

        # 7. AIModelCallConfig
        model_call_config = None
        # -------------------
        if settings.model_call_config:
            model_call_config = settings.model_call_config
            model_call_config.options = options  # Override the refined options
        else:
            # user_id = "usr_id_abcd"  # TODO_FUTURE
            model_call_config = AIModelCallConfig(
                streaming=streaming,
                max_output_tokens=max_output_tokens,
                reasoning=reasoning,
                max_reasoning_tokens=max_reasoning_tokens,
                options=options,
                # metadata={"user_id": user_id},
                test_mode=test_mode,
            )

        # Add model call config details to tracing
        if model_call_config:
            config_data = {
                "streaming": model_call_config.streaming,
                "max_output_tokens": getattr(model_call_config, "max_output_tokens", None),
                "reasoning": getattr(model_call_config, "reasoning", False),
            }

            if hasattr(model_call_config, "structured_output") and model_call_config.structured_output:
                config_data["has_structured_output"] = True
                if hasattr(model_call_config.structured_output, "output_schema"):
                    schema_name = getattr(
                        model_call_config.structured_output.output_schema,
                        "__name__",
                        str(model_call_config.structured_output.output_schema),
                    )
                    config_data["structured_output_schema"] = schema_name

            add_trace_attribute(model_call_config_attr, config_data)

        # 8. Call model
        # -------------------
        client = AIModelClient(
            is_async=True,
            model_endpoint=ai_model_ep,
            config=model_call_config,
        )

        # Add a trace attribute just before the API call
        add_trace_attribute(api_call_started_attr, datetime.now().isoformat())

        state_data = {
            "ai_model": ai_model_ep.ai_model.model_name,
            "api": ai_model_ep.api.provider,
            "model_call_config": model_call_config.model_dump(),
            "prompt": prompt,
            "context": context,
            "instructions": instructions,
        }

        # Dump  STATE for AI model calls for easy debugs
        execution_context.artifact_manager.record_data(
            record_type="state",
            data=state_data,
            record_settings=node_definition.record_settings.state,
            execution_context=execution_context,
        )

        # Make the API call
        response = await client.generate_async(
            prompt=prompt,
            context=context,
            instructions=instructions,
        )
        if not isinstance(response, AIModelCallResponse):
            logger.exception(
                f"Illegal response type for {type(response)} AIModel Call. Expected type is AIModelCallResponse"
            )

        # Add API response metadata to tracing
        if hasattr(response, "full_response") and hasattr(response.full_response, "usage_charge"):
            usage_charge = response.full_response.usage_charge
            charge_data = usage_charge.model_dump() if hasattr(usage_charge, "model_dump") else str(usage_charge)

            # Extract cost with consistent formatting regardless of notation
            cost = charge_data.get("cost", None)
            if cost is not None:
                formatted_cost = f"${float(cost):.6f}"  # Convert to float and format with 6 decimal places
            else:
                formatted_cost = "$?"

            # Same for charge if needed
            charge = charge_data.get("charge", None)
            if charge is not None:
                formatted_charge = f"${float(charge):.6f}"
            else:
                formatted_charge = "$?"

            add_trace_attribute(cost_attr, formatted_cost)
            add_trace_attribute(charge_attr, formatted_charge)

        if streaming:
            if not isinstance(response.stream_generator, AsyncGenerator):
                logger.exception(f"Streaming should return an AsyncGenerator, not {type(response)}")

            # stream_generator = response.stream_generator
            stream_generator = self.generate_stream_response(
                node_id=node_input,
                node_input=node_input,
                model_call_config=model_call_config,
                execution_context=execution_context,
                stream_generator=response.stream_generator,
            )
            execution_context.stream_generator = stream_generator
            return "abc"  # Should retrun a non None value: TODO_FUTURE: Fix this

        # Non streaming:
        # Get result
        result = self._derive_result(
            node_id=node_id,
            node_definition=node_definition,
            execution_context=execution_context,
            node_input=node_input,
            model_call_config=model_call_config,
            response=response,
            settings=settings,
        )

        return result

    def _derive_result(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        node_input: NodeInput,
        model_call_config: AIModelCallConfig,
        response: AIModelCallResponse,
        settings: AIModelNodeSettings,
    ) -> AIModelNodeExecutionResult:
        # Non streaming

        if response is None:
            return self.set_node_execution_failed(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
                message=("Response in None"),
            )

        logger.debug(
            f"call_ai_model: status={response.status if response else 'FAIL'}, "
            f"Preview of response={response.preview_dict()},"
        )
        node_output = NodeOutput[AIModelNodeOutputData](
            data=AIModelNodeOutputData(
                response=response,
            )
        )

        # Fill output and outcome in execution context
        text_outcome = None
        structured_outcome = None
        files = []

        if response.chat_response:
            if model_call_config.structured_output is not None:
                structured_outcome = response.chat_response.structured()
                if not structured_outcome:
                    logger.error("AIModelNode structured_outcome is None when node settings sets structured_output")

                if not isinstance(structured_outcome, dict):
                    logger.error(f"AIModelNode structured_outcome is not a dict but of type {type(structured_outcome)}")
            else:
                text_outcome = response.chat_response.text()
        elif response.image_response:
            if settings.save_generated_bytes:
                path = DADTemplateEngine.render_dad_template(
                    template=settings.bytes_save_path,
                    variables={},
                    execution_context=execution_context,
                )
                path = str(path)  # Should be string
                filename_prefix = DADTemplateEngine.render_dad_template(
                    template=settings.bytes_save_filename_prefix,
                    variables={},
                    execution_context=execution_context,
                )
                filename_prefix = str(filename_prefix)  # Should be string
                index = 0

                def _get_timestamp_sig(_prefix):
                    import uuid

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    # return f"{_prefix}_{timestamp}"
                    return f"{_prefix}_{timestamp}__{uuid.uuid4().hex[:6]}"

                for choice in response.image_response.choices:
                    for image_content in choice.contents:
                        _prefix = f"{filename_prefix}_{index}"
                        _filename = _get_timestamp_sig(_prefix)
                        _filename = f"{_filename}.png"
                        if image_content.content_format == ImageContentFormat.BASE64:
                            import base64

                            # Convert base64 to image
                            image_bytes = base64.b64decode(image_content.content_b64_json)

                        elif image_content.content_format == ImageContentFormat.BYTES:
                            ## Directly use the bytes data
                            image_bytes = image_content.content_bytes

                        elif image_content.content_format == ImageContentFormat.URL:
                            logger.error("Image content format `url` is not supported with `save_generated_bytes` ")
                            continue
                        else:
                            logger.error(
                                f"Unknonw Image content format `{image_content.content_format}` "
                                "with `save_generated_bytes` "
                            )
                            continue

                        # save_file
                        _saved = execution_context.artifact_manager.record_data(
                            record_type="file",
                            data=image_bytes,
                            record_settings=RecordSettingsItem(
                                enabled=True,
                                path=path,
                                filename=_filename,
                                file_format=RecordFileFormatEnum.image,
                            ),
                            execution_context=execution_context,
                        )
                        if _saved:
                            files.append(
                                StoredFile(
                                    name=_filename,
                                    path=path,
                                )
                            )
                        else:
                            logger.error(f"Failed to save byte to {path} when save_generated_bytes is set")

        node_outcome = AIModelNodeOutcome(
            text=text_outcome,
            structured=structured_outcome,
            files=files,
        )

        status = ExecutionStatusEnum.COMPLETED if response.status.successful else ExecutionStatusEnum.FAILED
        return AIModelNodeExecutionResult(
            node_identifier=node_id,
            execution_status=status,
            input=node_input,
            output=node_output,
            outcome=node_outcome,
            created_at=datetime.now(),
        )

    async def generate_stream_response(
        self,
        node_id: NodeID,
        node_input: NodeInput,
        model_call_config: AIModelCallConfig,
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

                        result = self._derive_result(
                            node_id=node_id,
                            node_input=node_input,
                            model_call_config=model_call_config,
                            response=final_response,
                        )

                    # NOTE: `await`
                    await execution_context.notify_streaming_complete(
                        identifier=node_id,
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
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
    ) -> list:
        settings = node_definition.settings
        context_sources = settings.context_sources if settings and settings.context_sources else []
        outputs_as_prompts = []
        try:
            for source_node_identifier in context_sources:
                if source_node_identifier == SpecialNodeIDEnum.PREVIOUS:
                    previous_node_identifier = execution_context.component_definition.get_previous_element_id(
                        execution_context.current_node_identifier,
                    )
                    previous_node_execution_result = execution_context.execution_results.get(previous_node_identifier)
                else:
                    previous_node_execution_result = execution_context.execution_results.get(source_node_identifier)

                previous_node_output = previous_node_execution_result.output.data

                prompt = previous_node_output.response.full_response.to_prompt()

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
        if not execution_context.resource_config:
            raise ValueError("resource_config must be set for ai_model_call")

        result = await self._call_ai_model(
            node_definition=node_definition,
            node_input=node_input,
            execution_context=execution_context,
            streaming=True,
        )
        return result
