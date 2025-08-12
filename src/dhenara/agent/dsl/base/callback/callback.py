import inspect
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import Field

from dhenara.agent.dsl.base import ContextT, Executable, ExecutableTypeEnum, NodeID
from dhenara.agent.dsl.base.data.dad_template_engine import DADTemplateEngine
from dhenara.agent.types.base import BaseModel


# A generic node that could later be specialized
class ExecutableCallback(Executable, BaseModel):
    """
    A single execution callback.
    Wraps a node custom fn in between nodes/ components.
    """

    id: NodeID = Field(
        ...,
        description="Unique human readable identifier for the node",
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

    async def execute(self, execution_context: ContextT) -> Any:
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

            final_args = {**self.args, **final_template_args}
            result = self.callable_definition(**final_args)

            # Await if the callable is async fns
            if inspect.isawaitable(result):
                _result = await result
                return _result

            # Callable is sync fn
            return result
        except Exception as e:
            raise ValueError(f"Error while executing callback. {e}.")


CallbackT = TypeVar("CallbackT", bound=ExecutableCallback)
