import json
import logging
from pathlib import Path

from dhenara.agent.dsl.base import ExecutionContext
from dhenara.agent.dsl.base.data.dad_template_engine import DADTemplateEngine

logger = logging.getLogger(__name__)


class FileSytemOperationsMixin:
    def get_formatted_base_directory(
        self,
        node_input,
        settings,
        execution_context: ExecutionContext,
    ) -> Path:
        """Format path with variables."""
        variables = {}

        # Determine base directory from input or settings
        base_directory = "."
        if hasattr(node_input, "base_directory") and node_input.base_directory:
            base_directory = node_input.base_directory
        elif hasattr(settings, "base_directory") and settings.base_directory:
            base_directory = settings.base_directory

        # Resolve base directory with variables
        path_str = DADTemplateEngine.render_dad_template(
            template=base_directory,
            variables=variables,
            execution_context=execution_context,
        )

        return Path(path_str).expanduser().resolve()

    def _get_allowed_directories(self, node_input, settings) -> list[str]:
        """Get the list of allowed directories."""
        allowed_dirs = []

        # Check input first, then settings
        if hasattr(node_input, "allowed_directories") and node_input.allowed_directories:
            allowed_dirs = node_input.allowed_directories
        elif hasattr(settings, "allowed_directories") and settings.allowed_directories:
            allowed_dirs = settings.allowed_directories

        # If no directories specified, return empty list
        if not allowed_dirs:
            return []

        # Normalize paths
        return [str(Path(d).expanduser().resolve()) for d in allowed_dirs]
        # return [os.path.normpath(os.path.abspath(d)) for d in allowed_dirs]

    def _extract_operations(
        self,
        node_input,
        settings,
        execution_context: ExecutionContext,
        operation_class,  # FileOperation
    ) -> list:
        """Extract file operations from various sources."""
        operations = []

        # Extract operations from operations_template if provided
        if settings.operations_template is not None:
            template_result = DADTemplateEngine.render_dad_template(
                template=settings.operations_template,
                variables={},
                execution_context=execution_context,
            )

            # Process operations based on the actual type returned
            if template_result:
                try:
                    # Handle list of operations
                    if isinstance(template_result, list):
                        operations = []
                        for op in template_result:
                            if isinstance(op, dict):
                                operations.append(operation_class(**op))
                            elif isinstance(op, operation_class):
                                operations.append(op)
                            else:
                                logger.error(f"Unexpected operation type in list: {type(op)}")
                    # Handle single operation as dict
                    elif isinstance(template_result, dict):
                        operations = [operation_class(**template_result)]
                    # Handle JSON string
                    elif isinstance(template_result, str):
                        try:
                            # Try parsing as JSON
                            parsed_ops = json.loads(template_result)
                            if isinstance(parsed_ops, list):
                                operations = [operation_class(**op) for op in parsed_ops]
                            elif isinstance(parsed_ops, dict):
                                operations = [operation_class(**parsed_ops)]
                            else:
                                logger.error(f"Unexpected structure in JSON string: {type(parsed_ops)}")
                        except json.JSONDecodeError:
                            logger.error(f"Unable to parse operations from template string: {template_result}")
                    # Handle other unexpected types
                    else:
                        logger.error(f"Unsupported template result type: {type(template_result)}")
                except Exception as e:
                    logger.error(f"Error processing operations from template: {e}", exc_info=True)

        # If no operations from template, try other sources
        if not operations:
            # Get operations from different possible sources
            if hasattr(node_input, "json_operations") and node_input.json_operations:
                # Parse JSON operations
                try:
                    ops_data = json.loads(node_input.json_operations)
                    if isinstance(ops_data, dict) and "operations" in ops_data:
                        operations = [operation_class(**op) for op in ops_data["operations"]]
                    elif isinstance(ops_data, list):
                        operations = [operation_class(**op) for op in ops_data]
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON in operations: {e}")
            elif hasattr(node_input, "operations") and node_input.operations:
                operations = node_input.operations
            elif hasattr(settings, "operations") and settings.operations:
                operations = settings.operations

        return operations

    def _validate_paths(
        self,
        base_directory: Path,
        operations: list,
        allowed_dirs: list[str],
        use_relative_paths: bool,
    ) -> None:
        """
        Validate paths for security concerns.
        Ensures all file operations are within allowed directories.
        """
        if not allowed_dirs:
            return  # No restrictions if no allowed directories specified

        for op in operations:
            # Check relevant paths based on operation type
            paths_to_check = []

            if hasattr(op, "path") and op.path:
                paths_to_check.append(op.path)
            if hasattr(op, "paths") and op.paths:
                paths_to_check.extend(op.paths)
            if hasattr(op, "source") and op.source:
                paths_to_check.append(op.source)
            if hasattr(op, "destination") and op.destination:
                paths_to_check.append(op.destination)

            for path_str in paths_to_check:
                # Get absolute path
                if Path(path_str).is_absolute():
                    if use_relative_paths:
                        raise ValueError(f"Absolute path is given when use_relative_paths is set for path {path_str}")

                    full_path = Path(op.path).resolve()
                else:
                    full_path = (base_directory / path_str).resolve()

                # Check if path is within allowed directories
                path_allowed = False
                for allowed_dir in allowed_dirs:
                    allowed_path = Path(allowed_dir).resolve()
                    try:
                        # Check if path is within allowed directory
                        if str(full_path).startswith(str(allowed_path)):
                            path_allowed = True
                            break
                    except Exception:
                        # Skip invalid paths
                        continue

                if not path_allowed:
                    raise ValueError(f"Access denied - path outside allowed directories: {full_path}")
