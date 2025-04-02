import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from dhenara.agent.dsl.base import (
    DADTemplateEngine,
    ExecutableNodeDefinition,
    ExecutionContext,
    ExecutionStatusEnum,
    NodeExecutionResult,
    NodeID,
    NodeInput,
    NodeOutput,
    SpecialNodeIDEnum,
    StreamingStatusEnum,
)
from dhenara.agent.dsl.flow import FlowNodeExecutor, FlowNodeTypeEnum
from dhenara.agent.dsl.inbuilt.flow_nodes.ai_model import (
    AIModelNodeInput,
    AIModelNodeOutcome,
    AIModelNodeOutputData,
    AIModelNodeSettings,
    ai_model_node_tracing_profile,
)
from dhenara.agent.observability.tracing import trace_node
from dhenara.agent.observability.tracing.data import TracingDataCategory, add_trace_attribute, trace_collect
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
    _tracing_profile = ai_model_node_tracing_profile

    def __init__(self):
        super().__init__(identifier="ai_model_node_executor")
        self.resource_config: ResourceConfig | None = None

    @trace_node(FlowNodeTypeEnum.ai_model_call.value)
    async def execute_node(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        node_input: NodeInput,
        resource_config: ResourceConfig,
    ) -> NodeExecutionResult[AIModelNodeOutputData]:
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
        resources_override = node_input.resources if node_input and node_input.resources_override else []

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
                (resource for resource in node_definition.resources if resource.is_default),
                None,
            )

        if not node_resource:
            raise ValueError("No default resource found in flow node configuration")

        add_trace_attribute(
            "node_resource",
            getattr(node_resource, "item_type", "unknown"),
            TracingDataCategory.secondary,
        )
        # Add query information if available
        if hasattr(node_resource, "query"):
            add_trace_attribute("node_resource", node_resource.query, TracingDataCategory.secondary)

        # 2. Fix Setting
        # -------------------
        settings: AIModelNodeSettings = node_definition.select_settings(node_input=node_input)
        if settings is None or not isinstance(settings, AIModelNodeSettings):
            raise ValueError(f"Invalid setting for node. selected settings is: {settings}")

        # 3. Fix AI Model endpoint
        # -------------------
        ai_model_ep = self.resource_config.get_resource(node_resource)
        add_trace_attribute("model_endpoint_id", getattr(ai_model_ep, "id", "unknown"), TracingDataCategory.primary)
        add_trace_attribute("model_name", getattr(ai_model_ep, "model_name", "unknown"), TracingDataCategory.primary)

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
            dad_dynamic_variables=execution_context.get_dad_dynamic_variables(),
            run_env_params=execution_context.run_context.run_env_params,
            node_execution_results=execution_context.execution_results,
            mode="expression",
        )

        # Add the final prompt to tracing
        add_trace_attribute(
            "final_prompt",
            prompt.text if hasattr(prompt, "text") else str(prompt),
            TracingDataCategory.primary,
        )

        # TODO: template support for instructions and context?
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
        add_trace_attribute("system_instructions", instructions, TracingDataCategory.primary)

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
            add_trace_attribute("context_count", len(context), TracingDataCategory.secondary)
            # Add preview of first few context items
            for i, ctx in enumerate(context[:3]):
                add_trace_attribute(
                    f"context[{i}]",
                    ctx.text if hasattr(ctx, "text") else str(ctx),
                    TracingDataCategory.secondary,
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
        add_trace_attribute("model_options", options, TracingDataCategory.secondary)
        add_trace_attribute("test_mode", test_mode, TracingDataCategory.tertiary)

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

            add_trace_attribute("model_call_config", config_data, TracingDataCategory.secondary)

        # 8. Call model
        # -------------------
        client = AIModelClient(
            is_async=True,
            model_endpoint=ai_model_ep,
            config=model_call_config,
        )

        # Add a trace attribute just before the API call
        add_trace_attribute("api_call_started", datetime.now().isoformat(), TracingDataCategory.tertiary)

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

            add_trace_attribute("cost", formatted_cost, TracingDataCategory.primary)
            add_trace_attribute("charge", formatted_charge, TracingDataCategory.primary)

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
            return "abc"  # Should retrun a non None value: TODO: Fix this

        # Non streaming:
        # Get result
        result = self._derive_result(
            node_id=node_id,
            node_definition=node_definition,
            execution_context=execution_context,
            node_input=node_input,
            model_call_config=model_call_config,
            response=response,
        )

        self.update_execution_context(
            node_id=node_id,
            execution_context=execution_context,
            result=result,
        )

        return result

    def _derive_result(
        self,
        node_id: NodeID,
        node_definition: ExecutableNodeDefinition,
        execution_context: ExecutionContext,
        node_input: NodeInput,
        model_call_config: AIModelCallConfig,
        response,
    ) -> NodeExecutionResult:
        # Non streaming

        if response is None:
            return self.set_node_execution_failed(
                node_id=node_id,
                node_definition=node_definition,
                execution_context=execution_context,
                message=("Response in None"),
            )

        logger.debug(f"call_ai_model: status={response.status if response else 'FAIL'}, response={response},")
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

        node_outcome = AIModelNodeOutcome(
            text=text_outcome,
            structured=structured_outcome,
        )

        status = ExecutionStatusEnum.COMPLETED if response.status.successful else ExecutionStatusEnum.FAILED
        return NodeExecutionResult[AIModelNodeOutputData](
            node_identifier=node_id,
            status=status,
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

                previous_node_output = previous_node_execution_result.node_output.data

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
