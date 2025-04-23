# Template Engine Documentation

## Quick Start

The Template Engine allows you to create dynamic text with variable substitution and complex expressions.

```python
from your_module import TemplateEngine

# Simple variable substitution
result = TemplateEngine.render_template("Hello $var{name}!", {"name": "World"})
# Output: "Hello World!"

# Expression evaluation
result = TemplateEngine.render_template(
    "Status: $expr{user.active ? 'Online' : 'Offline'}",
    {"user": {"active": True}}
)
# Output: "Status: Online"

# Accessing data properties
result = TemplateEngine.render_template(
    "You have $expr{cart.items.length} items worth $expr{cart.total} in your cart.",
    {"cart": {"items": ["item1", "item2"], "total": 25.99}}
)
# Output: "You have 2 items worth 25.99 in your cart."
```

## Template Syntax

### Variable Substitution: `$var{}`

The simplest form of substitution that replaces a variable placeholder with its value.

```
$var{variable_name}
```

Example:
```python
TemplateEngine.render_template("Welcome, $var{username}!", {"username": "Alice"})
# Output: "Welcome, Alice!"
```

### Expression Evaluation: `$expr{}`

Evaluates expressions and replaces the placeholder with the result.

```
$expr{expression}
```

Expressions can include:
- Property access with dot notation
- Array/list indexing
- Comparison and logical operators
- Conditional operations

Example:
```python
TemplateEngine.render_template(
    "Account: $expr{user.premium ? 'Premium' : 'Basic'}",
    {"user": {"premium": True}}
)
# Output: "Account: Premium"
```

### Escape Sequences

To include literal template syntax in your output:

- `$$var{}` → renders as `$var{}`
- `$$expr{}` → renders as `$expr{}`

Example:
```python
TemplateEngine.render_template("Template syntax: $$var{name}", {})
# Output: "Template syntax: $var{name}"
```

## Data Access

### Property Access

Access nested properties using dot notation:

```python
TemplateEngine.render_template(
    "Address: $expr{user.address.city}",
    {"user": {"address": {"city": "New York"}}}
)
# Output: "Address: New York"
```

### Array/List Indexing

Access array elements using square brackets:

```python
TemplateEngine.render_template(
    "First item: $expr{items[0]}",
    {"items": ["apple", "banana", "cherry"]}
)
# Output: "First item: apple"
```

## Operators

### Comparison Operators

- `==` - Equal to
- `!=` - Not equal to
- `>` - Greater than
- `<` - Less than
- `>=` - Greater than or equal to
- `<=` - Less than or equal to

Example:
```python
TemplateEngine.render_template(
    "Status: $expr{temperature > 30 ? 'Hot' : 'Pleasant'}",
    {"temperature": 35}
)
# Output: "Status: Hot"
```

### Logical Operators

- `&&` - Logical AND
- `||` - Logical OR (also serves as a fallback operator)

Example:
```python
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

### Parentheses for Grouping

Use parentheses to control evaluation order:

```python
TemplateEngine.render_template(
    "Result: $expr{(value > 10) && (value < 20)}",
    {"value": 15}
)
# Output: "Result: True"
```

## Python Expressions

For complex logic, use Python expressions with the `py:` prefix:

```python
TemplateEngine.render_template(
    "Average: $expr{py: sum(scores) / len(scores) if scores else 0}",
    {"scores": [85, 90, 95]}
)
# Output: "Average: 90.0"
```

### Available Functions in Python Mode

The following functions are available in Python expression mode:
- Basic functions: `len`, `str`, `int`, `float`, `bool`
- Collections: `list`, `dict`, `set`
- Iteration/filtering: `filter`, `map`, `all`, `any`, `sorted`, `enumerate`, `zip`, `range`
- Math: `sum`, `min`, `max`
- Inspection: `isinstance`, `getattr`, `hasattr`

Example:
```python
TemplateEngine.render_template(
    "Stats: $expr{py: {'min': min(values), 'max': max(values), 'avg': sum(values)/len(values)}}",
    {"values": [10, 20, 30, 40, 50]}
)
# Output: "Stats: {'min': 10, 'max': 50, 'avg': 30.0}"
```

## Node Hierarchy Access

### Direct Access in Regular Expressions

Access the node hierarchy directly:

```python
TemplateEngine.render_template(
    "Analysis: $expr{initial_repo_analysis.outcome.results}",
    variables,
    execution_context
)
```

### Access in Python Expressions

In Python expressions, prefix node paths with `$node.`:

```python
TemplateEngine.render_template(
    "Count: $expr{py: len($node.initial_repo_analysis.outcome.results)}",
    variables,
    execution_context
)
```

## Advanced Features

### Conditional Output Based on Node Data

```python
TemplateEngine.render_template(
    "Status: $expr{py: 'Complete' if len($node.analysis.children) > 5 else 'Incomplete'}",
    variables,
    execution_context
)
```

### Complex Filtering and Validation

```python
TemplateEngine.render_template(
    "Quality: $expr{py: 'High' if all(child.word_count > 20 for child in $node.analysis.children) else 'Low'}",
    variables,
    execution_context
)
```

### Word Count Limiting

Limit the output to a specific number of words:

```python
TemplateEngine.render_template(
    "Long description: $expr{product.description}",
    {"product": {"description": "This is a very long product description that continues for many words"}},
    max_words=5
)
# Output: "Long description: This is a very long product"
```

## Error Handling

When expressions fail to evaluate, an error message is returned:

```python
TemplateEngine.render_template(
    "Result: $expr{nonexistent.property / 0}",
    {}
)
# Output: "Result: Error: 'nonexistent' not found"
```

## Best Practices

1. **Use fallback values** with the `||` operator to handle missing data:
   ```
   $expr{user.nickname || user.name || 'Anonymous'}
   ```

2. **Group complex expressions** with parentheses for clarity:
   ```
   $expr{(price > 100) && (discount > 0.1)}
   ```

3. **For complex logic**, use Python expressions rather than chained operators:
   ```
   $expr{py: 'High' if price > 100 and in_stock else 'Standard'}
   ```

4. **Escape template syntax** when you need to display it literally:
   ```
   To use variables, use the $$var{} syntax
   ```

5. **Validate template inputs** to prevent errors in production.