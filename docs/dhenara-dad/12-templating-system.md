# Dhenara Agent DSL (DAD) - Templating System

## Overview

The Dhenara Agent DSL (DAD) templating system is a powerful feature that enables dynamic content generation, variable substitution, and complex expression evaluation within agent definitions. This document explains the architecture of the templating system, its capabilities, and best practices for effective usage.

## Core Concepts

The DAD templating system operates on several key concepts:

1. **Variable Substitution**: Replace placeholders with variable values
2. **Expression Evaluation**: Evaluate expressions within templates
3. **Hierarchical References**: Access outputs from other nodes in the flow
4. **Conditional Logic**: Include conditional sections based on expression results

## Template Syntax

The templating system uses a distinctive syntax for different operations:

### Variable Substitution

Variable substitution uses the `$var{name}` syntax to replace placeholders with values:

```
"Generate code in $var{language} to implement $var{feature}"
```

When rendered, this replaces `$var{language}` and `$var{feature}` with their respective values.

### Expression Evaluation

Expression evaluation uses the `$expr{expression}` syntax to compute values:

```
"This will take $expr{processing_time * 2} minutes to complete"
```

Expressions can include basic arithmetic, string operations, and more complex operations.

### Hierarchical References

Hierarchical references use the `$hier{node_path.property}` syntax to access results from other nodes:

```
"Based on the analysis: $hier{analyzer_node.outcome.text}"
```

This allows nodes to reference outputs from previously executed nodes.

### Python Expressions

For more complex logic, Python expressions can be used with `$expr{py: python_code}`:

```
"Files found: $expr{py: len($hier{repo_analysis}.outcome.structured.files)}"
```

This enables the full power of Python within templates.

## Templating Classes

### TemplateEngine

The `TemplateEngine` is the core class responsible for rendering and evaluating templates:

```python
class TemplateEngine:
    @classmethod
    def render_template(cls, template: str, variables: dict[str, Any], 
                       execution_context: Optional[ExecutionContext] = None, 
                       mode: Literal["standard", "expression"] = "expression", 
                       max_words: int | None = None, 
                       debug_mode: bool = False) -> str:
        """Render a template string with variable substitution and expression evaluation."""
        # Implementation...

    @classmethod
    def evaluate_template(cls, expr_template: str, variables: dict[str, Any], 
                         execution_context: Optional[ExecutionContext] = None, 
                         debug_mode: bool = False) -> Any:
        """Evaluate an expression template and return the result."""
        # Implementation...
```

### DADTemplateEngine

The `DADTemplateEngine` extends the base engine with DAD-specific features:

```python
class DADTemplateEngine(TemplateEngine):
    @classmethod
    def render_dad_template(cls, template: str | Prompt | TextTemplate | ObjectTemplate, 
                           variables: dict[str, Any], 
                           execution_context: ExecutionContext, 
                           mode: Literal["standard", "expression"] = "expression", 
                           max_words: int | None = None, 
                           max_words_file: int | None = None, 
                           debug_mode: bool = False, 
                           **kwargs: Any) -> Any:
        """Render a DAD-specific template."""
        # Implementation...
```

### Template Types

DAD supports several template types for different use cases:

1. **TextTemplate**: For string-based templates

```python
class TextTemplate(BaseModel):
    text: str
    variables: dict[str, Any] = Field(default_factory=dict)
```

2. **ObjectTemplate**: For templates that evaluate to objects

```python
class ObjectTemplate(BaseModel):
    expression: str
```

3. **Prompt**: For AI model prompts

```python
class Prompt(BaseModel):
    role: PromptMessageRoleEnum = PromptMessageRoleEnum.USER
    text: str | PromptText
    variables: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] | None = None
```

## Templating in Node Definitions

### AIModelNode Templates

Templates are commonly used in AI model node prompts:

```python
AIModelNode(
    resources=ResourceConfigItem.with_models("claude-3-7-sonnet"),
    settings=AIModelNodeSettings(
        system_instructions=[
            "You are a $var{role} specialized in $var{domain}.",
        ],
        prompt=Prompt.with_dad_text(
            text=(
                "Based on the following repository analysis:\n\n"
                "$hier{repo_analysis}.outcome.structured\n\n"
                "Implement a $var{feature_type} feature for $var{target_component}"
            ),
            variables={
                "feature_type": "search",
                "target_component": "user dashboard"
            }
        ),
    ),
)
```

The variables can be specified directly or provided through input handlers.

### FileOperationNode Templates

Templates are used in file operation nodes to specify operations:

```python
FileOperationNode(
    settings=FileOperationNodeSettings(
        base_directory=repo_dir,
        operations_template=ObjectTemplate(
            expression="$hier{code_generator}.outcome.structured.file_operations"
        ),
        commit_message="$var{run_id}: Implemented $var{feature_name}",
    ),
)
```

This allows file operations to be dynamically determined by previous nodes.

### FolderAnalyzerNode Templates

Templates can be used in folder analyzer settings:

```python
FolderAnalyzerNode(
    settings=FolderAnalyzerSettings(
        base_directory="$var{repo_dir}",
        operations=[
            FolderAnalysisOperation(
                operation_type="analyze_folder",
                path="$var{target_dir}",
                include_patterns=["*.py", "*.md"],
                exclude_patterns=["__pycache__"],
            )
        ],
    ),
)
```

## Advanced Templating Features

### Conditional Templates

Conditional logic can be implemented using Python expressions:

```python
"$expr{py: 'High priority' if priority > 8 else 'Normal priority'}"
```

### List Comprehensions

Lists can be manipulated using comprehensions:

```python
"Files: $expr{py: ', '.join([f.name for f in $hier{analysis}.outcome.structured.files if f.size > 1000])}"
```

### JSON Processing

JSON data can be extracted and manipulated:

```python
"$expr{py: json.loads($hier{api_call}.outcome.text)['results'][0]['title']}"
```

### Template Composition

Templates can be composed hierarchically:

```python
"$expr{py: render_template('Template with $var{name}', {'name': 'nested variable'})}"
```

## Execution Context Integration

The templating system is deeply integrated with the execution context, allowing templates to access results from any node in the execution hierarchy:

```python
# Access result from a node in the same flow
"$hier{node_id}.outcome.text"

# Access result from a node in a different flow
"$hier{flow_id.node_id}.outcome.structured.property"

# Access result from a node in a subagent
"$hier{agent_id.flow_id.node_id}.outcome.structured.property"
```

This enables powerful data flow between components.

## Variable Resolution

When resolving variables, the templating system follows this order:

1. Variables explicitly provided in the template definition
2. Variables provided through input handlers
3. Variables from the execution context
4. Default values if specified

```python
# Variable with a default value
"$var{threshold:0.75}"

# Variable with type conversion
"$var{count:int}"
```

## Best Practices

### Template Organization

1. **Maintain Readability**: Format complex templates for readability
2. **Modularize**: Break complex templates into smaller pieces
3. **Document Variables**: Document expected variables and their formats
4. **Error Handling**: Include fallbacks for missing variables

### Performance Considerations

1. **Avoid Deep Nesting**: Deeply nested templates can be slower to render
2. **Lazy Evaluation**: Use `ObjectTemplate` for values that should be evaluated only when needed
3. **Caching**: Consider caching results of expensive template evaluations

### Security Considerations

1. **Sanitize Inputs**: Be careful with user-provided inputs in templates
2. **Limit Python Expressions**: Consider limiting Python expression capabilities in production
3. **Execution Boundaries**: Respect execution boundaries for hierarchical references

## Debugging Templates

The templating system supports debug mode for troubleshooting:

```python
# Enable debug mode
result = TemplateEngine.render_template(template, variables, debug_mode=True)
```

In debug mode, the engine will print detailed information about variable substitution and expression evaluation.

## Extending the Templating System

The templating system can be extended with custom functions and filters:

```python
# Register a custom function
DADTemplateEngine.register_function("my_function", lambda x: process(x))

# Use in templates
"$expr{my_function(value)}"
```

This allows for domain-specific template extensions.

## Conclusion

The DAD templating system provides a powerful mechanism for creating dynamic, context-aware agent definitions. By leveraging variable substitution, expression evaluation, and hierarchical references, templates enable sophisticated data flow between components while maintaining readability and reusability.