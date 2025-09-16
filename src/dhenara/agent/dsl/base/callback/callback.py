import inspect
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

from pydantic import Field

from dhenara.agent.dsl.base import (
    CallbackInput,
    CallbackOutcome,
    CallbackOutput,
    CallbackOutputData,
    ContextT,
    Executable,
    ExecutableTypeEnum,
    ExecutionStatusEnum,
    NodeExecutionResult,
    NodeID,
)
from dhenara.agent.dsl.base.data.dad_template_engine import DADTemplateEngine
from dhenara.agent.dsl.base.node.node_settings import DEFAULT_OUTCOME_RECORD_SETTINGS, DEFAULT_RESULT_RECORD_SETTINGS
from dhenara.agent.observability import log_with_context, record_metric
from dhenara.agent.types.base import BaseModel

logger = logging.getLogger(__name__)


class CallbackExecutionResult(NodeExecutionResult[CallbackInput, CallbackOutput, CallbackOutcome]):
    executable_type: ExecutableTypeEnum = Field(default=ExecutableTypeEnum.callback)


# A generic node that could later be specialized
class ExecutableCallback(Executable, BaseModel):
    """
    A single execution callback.
    Wraps a node custom fn in between nodes/ components.
    """

    id: NodeID = Field(
        ...,
        description="Unique human readable identifier for the callback",
        min_length=1,
        max_length=150,
        pattern="^[a-zA-Z0-9_]+$",
    )

    callable_definition: Callable

    args: dict = Field(default_factory=dict)
    template_args: dict = Field(default_factory=dict)

    @property
    def executable_type(self) -> ExecutableTypeEnum:
        return ExecutableTypeEnum.callback

    async def execute(self, execution_context: ContextT) -> CallbackExecutionResult:
        # Record start time for metrics
        start_time = datetime.now()

        callback_id = self.id
        log_with_context(
            logger,
            logging.DEBUG,
            "Starting callback",
            {"callback_id": str(callback_id), "callable": self.callable_definition},
        )

        result = await self.execute_callback(execution_context=execution_context)

        # Set the result in the execution context
        execution_context.set_result(callback_id, result)

        # Record metrics
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        record_metric(
            meter_name="dhenara.dad.callback",
            metric_name="callback_execution_duration",
            value=duration_ms,
            metric_type="histogram",
            attributes={"callback_id": str(callback_id), "callable": self.callable_definition},
        )

        # Record success/failure metrics
        if result is not None:
            record_metric(
                meter_name="dhenara.dad.callback",
                metric_name="callback_execution_success",
                value=1,
                attributes={"callback_id": str(callback_id), "callable": self.callable_definition},
            )
        else:
            record_metric(
                meter_name="dhenara.dad.callback",
                metric_name="callback_execution_failure",
                value=1,
                attributes={"callback_id": str(callback_id), "callable": self.callable_definition},
            )

        log_with_context(
            logger,
            logging.DEBUG,
            f"callback Execution completed in {duration_ms:.2f}ms",
            {"callback_id": str(callback_id), "duration_ms": duration_ms, "has_result": result is not None},
        )

        return await self.record_results(
            execution_context=execution_context,
        )

    async def load_from_previous_run(self, execution_context: ContextT) -> Any:
        execution_context.logger.info(f"Loading previous run data for callback {self.id} ")

        result_data = await execution_context.load_from_previous_run(
            copy_artifacts=True,
        )

        if result_data:
            try:
                result = CallbackExecutionResult(**result_data)
                # Set the result in the execution context
                execution_context.set_result(self.id, result)

                return result
            except Exception as e:
                execution_context.logger.error(f"Failed to load previous run data for callback {self.id}: {e}")
                return None
        else:
            execution_context.logger.error(
                f"Falied to load data from previous execution result artifacts for callback {self.id}"
            )
            return None

    # ----------- Fns usually present inside an exectuor
    # -------------------------------------------------------------------------
    async def execute_callback(
        self,
        execution_context: ContextT,
    ) -> CallbackExecutionResult:
        """
        Handle the execution of a callback.
        """
        final_template_args = {}

        try:
            for key, val_template in self.template_args.items():
                if val_template is not None:
                    template_result = DADTemplateEngine.render_dad_template(
                        template=val_template,
                        variables={},
                        execution_context=execution_context,
                    )

                    # Process operations based on the actual type returned
                    if template_result:
                        final_template_args[key] = template_result

            # Provide a lightweight helper to allow callback author to persist custom artifacts
            def custom_artifact_dump(file_name: str, data: Any, subdir: str | None = None) -> bool:
                am = getattr(execution_context, "artifact_manager", None)
                if not am:
                    logger.debug("custom_artifact_dump: artifact_manager not available; skipping save")
                    return False
                return am.record_custom_artifact(
                    file_name=file_name,
                    data=data,
                    execution_context=execution_context,
                    subdir=subdir,
                )

            final_args = {**self.args, **final_template_args, "custom_artifact_dump": custom_artifact_dump}
            callable_result = self.callable_definition(**final_args)

            # Await if the callable is async fns
            if inspect.isawaitable(callable_result):
                callable_result = await callable_result

            # Create a serializable view of args (strip callables & modules)
            serializable_args = {
                k: v
                for k, v in final_args.items()
                if not callable(v) and v.__class__.__module__ != "types"  # exclude functions, lambdas, modules
            }

            # Create execution result
            result = CallbackExecutionResult(
                node_identifier=self.id,
                execution_status=ExecutionStatusEnum.COMPLETED,
                input=CallbackInput(final_args=serializable_args),
                output=CallbackOutput(data=CallbackOutputData(callable_result=callable_result)),
                outcome=CallbackOutcome(callable_result=callable_result),
                created_at=datetime.now(),
            )
            return result
        except Exception as e:
            err_msg = f"Error while executing callback. {e}."
            logger.error(err_msg)

            return CallbackExecutionResult(
                node_identifier=self.id,
                execution_status=ExecutionStatusEnum.FAILED,
                input=None,
                output=None,
                outcome=None,
                error=err_msg,
                created_at=datetime.now(),
            )

    async def record_results(
        self,
        execution_context: ContextT,
    ) -> None:
        if execution_context.artifact_manager:
            result: CallbackExecutionResult | None = execution_context.execution_results.get(self.id, None)

            if not result:
                logger.info("No result found in execution context. Skipping records")
                return False

            execution_context.updated_at = datetime.now()

            # Get record settings from the callback if available
            result_record_settings = DEFAULT_RESULT_RECORD_SETTINGS.model_copy(deep=True)
            outcome_record_settings = DEFAULT_OUTCOME_RECORD_SETTINGS.model_copy(deep=True)

            # NOTE:
            # When output is set in record settings, use it for recoring result which has
            #   1. Callback Input
            #   2. Callback Output
            #   3. Callback Outcome
            #   4. Callback Error

            # INFO:
            result_data = result.model_dump(
                mode="json",  # To avoid serialization errors (like dateatime)
            )

            # TODO_FUTURE: Avoid dulicate data recoding for outcome and input
            outcome_data = result.outcome
            outcome_data = outcome_data.model_dump() if hasattr(outcome_data, "model_dump") else outcome_data

            # Record the callback output
            execution_context.artifact_manager.record_data(
                record_type="result",
                data=result_data,
                record_settings=result_record_settings,
                execution_context=execution_context,
            )

            # Record the callback outcome
            execution_context.artifact_manager.record_data(
                record_type="outcome",
                data=outcome_data,
                record_settings=outcome_record_settings,
                execution_context=execution_context,
            )

        return None


CallbackT = TypeVar("CallbackT", bound=ExecutableCallback)
