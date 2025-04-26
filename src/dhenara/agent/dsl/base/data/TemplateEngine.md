# Template Engine Documentation

## Overview

The `TemplateEngine` is a powerful template system that provides variable substitution and complex expression evaluation capabilities. It supports hierarchical context access and complex expressions beyond what standard Python templating systems offer.

## Template Syntax

The engine supports three primary syntax patterns:

### 1. Variable Substitution: `$var{variable_name}`

Simple variable replacement from the provided context:

```python
TemplateEngine.render_template("Hello $var{name}!", {"name": "World"})
# Output: "Hello World!"
```

### 2. Expression Evaluation: `$expr{expression}`

Complex expressions with property access, operators, and conditional logic:

```python
TemplateEngine.render_template(
    "Status: $expr{user.active ? 'Online' : 'Offline'}",
    {"user": {"active": True}}
)
# Output: "Status: Online"
```

### 3. Hierarchical Access: `$hier{component.node_id}`

Access execution results from other components in the execution context:

```python
TemplateEngine.render_template(
    "Task: $expr{$hier{planner.plan_generator}.structured.task_name}",
    {},
    execution_context
)
# Output: "Task: Create project plan"
```

### Escape Sequences

To output literal template syntax in your text, use double dollar signs:

- `$$var{}` → renders as `$var{}`
- `$$expr{}` → renders as `$expr{}`
- `$$hier{}` → renders as `$hier{}`

```python
TemplateEngine.render_template("Template syntax: $$var{name}", {})
# Output: "Template syntax: $var{name}"
```

## Feature Details

### Property Access

Access nested properties using dot notation:

```python
TemplateEngine.render_template(
    "City: $expr{user.address.city}",
    {"user": {"address": {"city": "New York"}}}
)
# Output: "City: New York"
```

### Array/List Indexing

Access array elements using bracket notation:

```python
TemplateEngine.render_template(
    "First item: $expr{items[0]}",
    {"items": ["apple", "banana", "cherry"]}
)
# Output: "First item: apple"
```

### Supported Operators

#### Comparison Operators

- `==` - Equal to
- `!=` - Not equal to
- `>` - Greater than
- `<` - Less than
- `>=` - Greater than or equal to
- `<=` - Less than or equal to

#### Logical Operators

- `&&` - Logical AND
- `||` - Logical OR (also serves as a fallback operator)

Example:

```python
# Logical AND
TemplateEngine.render_template(
    "Access: $expr{user.active && user.permissions.admin}",
    {"user": {"active": True, "permissions": {"admin": False}}}
)
# Output: "Access: False"

# Using || as fallback
TemplateEngine.render_template(
    "Display name: $expr{user.nickname || user.name}",
    {"user": {"name": "John", "nickname": None}}
)
# Output: "Display name: John"
```

### Python Expression Mode

For advanced logic, use Python expressions with the `py:` prefix:

```python
TemplateEngine.render_template(
    "Average: $expr{py: sum(scores) / len(scores) if scores else 0}",
    {"scores": [85, 90, 95]}
)
# Output: "Average: 90.0"

# With hierarchical access
TemplateEngine.render_template(
    "Valid: $expr{py: $hier{planner.plan_generator}.structured is not None}",
    {}
)
# Output: "Valid: True"
```

#### Available Functions in Python Mode

The following functions are available in Python expression mode:

- Basic functions: `len`, `str`, `int`, `float`, `bool`, `list`, `dict`, `set`
- Math: `sum`, `min`, `max`
- Collection operations: `all`, `any`, `filter`, `sorted`, `enumerate`, `zip`, `range`
- Inspection: `isinstance`, `getattr`, `hasattr`, `map`

## API Reference

### `render_template`

```python
TemplateEngine.render_template(
    template: str,
    variables: dict[str, Any],
    execution_context: Optional[ExecutionContext] = None,
    mode: Literal["standard", "expression"] = "expression",
    max_words: int | None = None,
    debug_mode: bool = False,
) -> str
```

Renders a string template with context support, evaluating expressions and returning a string.

**Parameters:**

- `template`: String template containing variable/expression patterns
- `variables`: Dictionary of variables for substitution
- `execution_context`: Optional execution context for hierarchical lookups
- `mode`: "standard" for basic substitution only, "expression" for advanced evaluation
- `max_words`: Optional word limit for output text
- `debug_mode`: Enable debug logging

**Returns:** String with template expressions evaluated and replaced

### `evaluate_template`

```python
TemplateEngine.evaluate_template(
    expr_template: str,
    variables: dict[str, Any],
    execution_context: Optional[ExecutionContext] = None,
    debug_mode: bool = False,
) -> Any
```

Evaluates a template expression and returns the raw result of the evaluation, preserving its type.

**Parameters:**

- `expr_template`: Template expression to evaluate
- `variables`: Dictionary of variables for substitution
- `execution_context`: Optional execution context for hierarchical lookups
- `debug_mode`: Enable debug logging

**Returns:** Raw result of expression evaluation (preserves type)

## Error Handling

When expressions fail to evaluate, an error message is returned:

```python
TemplateEngine.render_template(
    "Result: $expr{nonexistent.property / 0}",
    {}
)
# Output: "Result: Error: 'nonexistent' not found"
```

## DAD Template Engine

The `DADTemplateEngine` extends the base `TemplateEngine` with additional context from RunEnvParams and node execution results specifically for the Dhenara Agent DSL (DAD).

### `render_dad_template`

```python
DADTemplateEngine.render_dad_template(
    template: str | Prompt | TextTemplate | ObjectTemplate,
    variables: dict[str, Any],
    execution_context: ExecutionContext,
    mode: Literal["standard", "expression"] = "expression",
    max_words: int | None = None,
    max_words_file: int | None = None,
    debug_mode: bool = False,
    **kwargs: Any,
) -> Any
```

Renders a template with DAD-specific context and hierarchical node resolution, supporting various template types.

## Best Practices

1. **Use fallback values** with the `||` operator for missing data:

   ```
   $expr{user.nickname || user.name || 'Anonymous'}
   ```

2. **Group complex expressions** with parentheses for clarity:

   ```
   $expr{(price > 100) && (discount > 0.1)}
   ```

3. **Use Python expressions** for complex logic:

   ```
   $expr{py: 'High' if price > 100 and in_stock else 'Standard'}
   ```

4. **Hierarchical access** for execution context data:

   ```
   $expr{$hier{component.node_id}.property}
   ```

5. **Set word limits** when appropriate to control output length:
   ```python
   TemplateEngine.render_template(template, variables, max_words=100)
   ```
