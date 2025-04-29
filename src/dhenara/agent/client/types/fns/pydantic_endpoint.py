from collections.abc import Callable
from functools import wraps
from inspect import Parameter, signature
from typing import Any, TypeVar, get_type_hints

from pydantic import ValidationError

from dhenara.agent.types.base import BaseModel

T = TypeVar("T", bound=BaseModel)


def pydantic_endpoint(model: type[T]) -> Callable:
    """
    Decorator to create endpoint methods supporting both model instance and kwargs.

    Supports:
    1. Passing a model instance directly
    2. Passing individual fields as kwargs
    3. Proper type hints and IDE support
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, data: T | None = None, **kwargs) -> Any:
            try:
                if data is not None:
                    if not isinstance(data, model):
                        raise ValueError(f"data must be an instance of {model.__name__}")
                    model_instance = data
                else:
                    model_instance = model(**kwargs)

                return func(self, model_instance=model_instance)

            except ValidationError as ve:
                raise ValueError(f"Invalid {model.__name__} data: {ve}") from ve

        # Update function signature for better IDE support

        # Create new parameters
        parameters = [
            Parameter(
                name="self",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Any,
            ),
            Parameter(
                name="data",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=model | None,
                default=None,
            ),
        ]

        # Add model fields as optional kwargs
        for field_name, field in model.model_fields.items():
            parameters.append(
                Parameter(
                    name=field_name,
                    kind=Parameter.KEYWORD_ONLY,
                    annotation=field.annotation | None,
                    default=None,
                ),
            )

        wrapper.__signature__ = signature(func).replace(parameters=parameters)
        wrapper.__annotations__ = {
            "data": model | None,
            "return": get_type_hints(func)["return"],
        }

        # Add detailed docstring
        base_doc = func.__doc__ or ""
        wrapper.__doc__ = f"""
        {base_doc}

        Args:
            data: Optional[{model.__name__}] - Complete model instance
            **kwargs: Individual field values matching {model.__name__} schema

        Either provide a complete `data` instance or individual fields via kwargs.

        Fields:
        {_format_model_fields(model)}

        Returns:
            {get_type_hints(func)["return"].__name__}

        Raises:
            ValueError: If the provided data is invalid
            APIError: If the API request fails
        """
        return wrapper

    return decorator


def _format_model_fields(model: type[BaseModel]) -> str:
    """Format model fields for documentation."""
    fields = []
    for name, field in model.model_fields.items():
        default = f" (default: {field.default})" if field.default else ""
        required = " (required)" if field.is_required else ""
        fields.append(f"    {name}: {field.annotation}{required}{default}")
    return "\n".join(fields)


def todo_old_pydantic_endpoint(model: type[T]) -> Callable:
    """Decorator to create endpoint methods from Pydantic models."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Create model instance from kwargs
            instance = model(**kwargs)
            return func(self, model_instance=instance)

        # Update the signature to match the model fields

        # Get model fields
        model_fields = model.model_fields

        # Create new parameters
        parameters = [
            Parameter(
                name="self",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Any,
            ),
        ]

        # Add parameters from model fields
        for field_name, field in model_fields.items():
            parameters.append(
                Parameter(
                    name=field_name,
                    kind=Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=field.annotation,
                    default=field.default if field.default else Parameter.empty,
                ),
            )

        wrapper.__signature__ = signature(func).replace(parameters=parameters)
        wrapper.__doc__ = func.__doc__ or model.__doc__
        return wrapper

    return decorator
