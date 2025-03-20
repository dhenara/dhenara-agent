import logging
from abc import abstractmethod
from typing import Any, ClassVar, NewType, Optional

from pydantic import Field

from dhenara.agent.types.base import BaseModelABC
from dhenara.agent.types.flow._node_io import FlowNodeInputs
from dhenara.ai.types.resource import ResourceConfig

ExecutableNodeID = NewType("ExecutableNodeID", str)


class ExecutionContext(BaseModelABC):
    """A generic execution context for any DSL execution."""

    results = Field(default_factory=dict)
    # initial_data: dict[ExecutableNodeID, Any] = Field(default_factory=dict)
    initial_inputs: FlowNodeInputs  # TODO_FUTURE: Make generic
    resource_config: ResourceConfig = None
    data: dict[str, Any] = Field(default_factory=dict)  # Add this
    parent: Optional["ExecutionContext"] = Field(default=None)
    results: dict[str, Any] = Field(default_factory=dict)
    artifact_manager: Any = Field(default=None)

    logger: ClassVar = logging.getLogger("dhenara.agent.execution_ctx")  # TODO: Pass correct id

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize data from initial_data if provided
        # if self.initial_data:
        #    self.data.update(self.initial_data)

    def get_value(self, path: str) -> Any:
        """Get a value from the context by path."""
        # Handle simple keys
        if "." not in path:
            if path in self.data:
                return self.data[path]
            if path in self.results:
                return self.results[path]
            if self.parent:
                return self.parent.get_value(path)
            return None

        # Handle nested paths
        parts = path.split(".")
        current = self.get_value(parts[0])

        for part in parts[1:]:
            if current is None:
                return None

            # Handle list indexing
            if isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            # Handle dictionary access
            elif isinstance(current, dict) and part in current:
                current = current[part]
            # Handle object attribute access
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current

    def set_result(self, key: str, value: Any) -> None:
        """Set a result value in the context."""
        self.results[key] = value

    def evaluate(self, expression: str) -> Any:
        """Evaluate an expression in this context."""
        # Simple variable reference
        if expression.startswith("$"):
            return self.get_value(expression[1:])

        # Template string with variables
        if "${" in expression:
            return self.evaluate_template(expression)

        # Python expression (with safety constraints)
        allowed_globals = {
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "sum": sum,
            "min": min,
            "max": max,
            "all": all,
            "any": any,
        }

        # Create a dictionary with context values
        eval_locals = {**self.data, **self.results}

        try:
            return eval(expression, {"__builtins__": allowed_globals}, eval_locals)
        except Exception as e:
            self.logger.error(f"Error evaluating expression '{expression}': {e}")
            return None

    def evaluate_template(self, template: str) -> str:
        """Evaluate a template string with variable substitutions."""
        result = template
        # Find all ${...} expressions
        import re

        for match in re.finditer(r"\${([^}]+)}", template):
            expr = match.group(1)
            value = self.evaluate(expr)
            result = result.replace(f"${{{expr}}}", str(value))
        return result

    @abstractmethod
    def create_iteration_context(self, iteration_data: dict[str, Any]) -> "ExecutionContext":
        """Create a new context for a loop iteration."""
        pass

    def merge_iteration_context(self, iteration_context: "ExecutionContext") -> None:
        """Merge results from an iteration context back to this context."""
        for key, value in iteration_context.results.items():
            iteration_key = f"{key}_{len([k for k in self.results if k.startswith(key + '_')])}"
            self.results[iteration_key] = value

    @abstractmethod
    async def record_outcome(self, node_def, result: Any) -> None:
        """Record the outcome of a node execution."""
        pass

    @abstractmethod
    async def record_iteration_outcome(self, loop_element, iteration: int, item: Any, result: Any) -> None:
        """Record the outcome of a loop iteration."""
        pass
