import ast
from pathlib import Path
from typing import Literal

DetailLevel = Literal["basic", "standard", "detailed", "full"]


class PythonStructureExtractor:
    """Extracts and analyzes Python code structure with configurable detail levels."""

    def __init__(self, file_path: Path):
        """Initialize with a Python file path."""
        self.file_path = file_path
        self.tree = None
        self._load_file()

    def _load_file(self) -> None:
        """Load and parse the Python file."""
        with open(self.file_path, encoding="utf-8") as f:
            content = f.read()
        self.tree = ast.parse(content)

    def extract(self, detail_level: DetailLevel = "basic") -> dict:
        """
        Extract Python code structure with the specified level of detail.

        Args:
            detail_level: Level of detail to extract:
                - "basic": Just imports, class names, function names (original behavior)
                - "standard": Adds signatures, inheritance, and docstrings
                - "detailed": Adds decorators, type hints, and nested definitions
                - "full": Includes everything plus simplified function bodies

        Returns:
            Dictionary containing the extracted structural elements
        """
        if not self.tree:
            self._load_file()

        result = {
            # "file_path": str(self.file_path),
            "module_docstring": ast.get_docstring(self.tree),
            "imports": self._extract_imports(),
            "classes": self._extract_classes(detail_level),
            "functions": self._extract_functions(detail_level),
        }

        # Add more details based on detail level
        if detail_level in ("detailed", "full"):
            result["constants"] = self._extract_constants()

        # if detail_level == "full":
        #    result["code_summary"] = self._generate_code_summary()

        return result

    def _extract_imports(self) -> list[str]:
        """Extract all import statements."""
        imports = []
        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.Import):
                imports.extend([f"import {name.name}" for name in node.names])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.extend([f"from {module} import {name.name}" for name in node.names])
        return imports

    def _extract_classes(self, detail_level: DetailLevel) -> list[dict]:
        """Extract class definitions with configurable detail."""

        classes = []
        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.ClassDef):
                class_info = {"name": node.name}

                # Add base classes if they exist
                if node.bases:
                    class_info["bases"] = [self._format_expression(base) for base in node.bases]

                # Add more details based on detail level
                if detail_level != "basic":
                    class_info["docstring"] = ast.get_docstring(node)

                    if detail_level in ("detailed", "full"):
                        # Extract methods
                        methods = []
                        class_variables = []

                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                method_info = self._extract_function_info(item, detail_level)
                                methods.append(method_info)
                            elif isinstance(item, ast.Assign) and detail_level in ("detailed", "full"):
                                class_variables.extend(
                                    [target.id for target in item.targets if isinstance(target, ast.Name)]
                                )

                        class_info["methods"] = methods

                        if class_variables:
                            class_info["class_variables"] = class_variables

                classes.append(class_info)
        return classes

    def _extract_functions(self, detail_level: DetailLevel) -> list[dict]:
        """Extract function definitions with configurable detail."""
        # Only include functions defined at module level (not methods inside classes)
        # We know they're at module level because we're iterating over the tree's direct children
        # Class fns are taken care inside _extract_classes
        return [
            self._extract_function_info(node, detail_level)
            for node in ast.iter_child_nodes(self.tree)
            if isinstance(node, ast.FunctionDef)
        ]

    def _extract_function_info(self, node: ast.FunctionDef, detail_level: DetailLevel) -> dict:
        """Extract detailed information about a function."""
        function_info = {"name": node.name}

        if detail_level != "basic":
            # Add signature details
            args = []
            for arg in node.args.args:
                arg_info = arg.arg

                # Add type annotations if present and detail level is sufficient
                if detail_level in ("detailed", "full") and arg.annotation:
                    arg_info += f": {self._format_expression(arg.annotation)}"

                args.append(arg_info)

            function_info["signature"] = f"{node.name}({', '.join(args)})"
            function_info["docstring"] = ast.get_docstring(node)

            # Add decorators if present and detail level is sufficient
            if detail_level in ("detailed", "full") and node.decorator_list:
                function_info["decorators"] = [self._format_expression(decorator) for decorator in node.decorator_list]

            # Add return type if present and detail level is sufficient
            if detail_level in ("detailed", "full") and node.returns:
                function_info["return_type"] = self._format_expression(node.returns)

            # For full detail, include simplified function body
            if detail_level == "full":
                # Extract high-level logic flow (not complete code)
                body_lines = []
                for item in node.body:
                    if isinstance(item, ast.Return):
                        body_lines.append("return statement")
                    elif isinstance(item, ast.If):
                        body_lines.append("conditional branch")
                    elif isinstance(item, ast.For):
                        body_lines.append("for loop")
                    elif isinstance(item, ast.While):
                        body_lines.append("while loop")
                    elif isinstance(item, ast.Try):
                        body_lines.append("exception handling")

                if body_lines:
                    function_info["body_structure"] = body_lines

        return function_info

    def _extract_constants(self) -> list[dict]:
        """Extract module-level constants."""
        constants = []
        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Check if name is uppercase (conventional for constants)
                        if target.id.isupper():
                            constants.append(
                                {
                                    "name": target.id,
                                    "value_type": type(ast.literal_eval(node.value)).__name__
                                    if isinstance(
                                        node.value, (ast.Str, ast.Num, ast.NameConstant, ast.List, ast.Dict, ast.Set)
                                    )
                                    else "complex_expression",
                                }
                            )
        return constants

    def _generate_code_summary(self) -> str:
        """Generate a high-level summary of what the code does."""
        # This is a simplified version - in a real implementation, you might use more
        # sophisticated analysis or even a small LLM call to summarize the code
        summary_parts = []

        if ast.get_docstring(self.tree):
            summary_parts.append(f"Module purpose: {ast.get_docstring(self.tree)}")

        class_count = len([n for n in ast.iter_child_nodes(self.tree) if isinstance(n, ast.ClassDef)])
        function_count = len([n for n in ast.iter_child_nodes(self.tree) if isinstance(n, ast.FunctionDef)])

        summary_parts.append(f"Contains {class_count} classes and {function_count} functions.")

        return " ".join(summary_parts)

    def _format_expression(self, expr: ast.expr) -> str:
        """Convert an AST expression to a string representation."""
        if isinstance(expr, ast.Name):
            return expr.id
        elif isinstance(expr, ast.Attribute):
            base = self._format_expression(expr.value)
            return f"{base}.{expr.attr}"
        elif isinstance(expr, ast.Call):
            func = self._format_expression(expr.func)
            return f"{func}(...)"
        elif isinstance(expr, ast.Subscript):
            value = self._format_expression(expr.value)
            return f"{value}[...]"
        else:
            # For other expressions, return a placeholder
            return "..."
