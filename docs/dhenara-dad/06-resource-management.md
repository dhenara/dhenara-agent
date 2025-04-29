# Dhenara Agent DSL (DAD) - Resource Management

## Resource Management Overview

Resource management in DAD provides a structured approach to managing AI models, API credentials, and other execution resources. The system allows for flexible configuration and runtime overrides of resources, making it easier to work with different environments and providers.

## Core Resource Management Components

### ResourceConfig

The `ResourceConfig` class is the central component for managing resources, particularly AI model configurations:

```python
from dhenara.ai.types.resource import ResourceConfig

# Create a resource configuration
resource_config = ResourceConfig()

# Load from a credentials file
resource_config.load_from_file(
    credentials_file="~/.dhenara/credentials.yaml",
    init_endpoints=True,
)
```

The credentials file typically contains API keys, endpoints, and default settings for different models and providers.

### ResourceRegistry

The `ResourceRegistry` manages resources of a specific type, allowing for global registration and thread-local overrides:

```python
from dhenara.agent.run.registry import resource_config_registry, model_registry

# Register a resource configuration
resource_config_registry.register("default", my_resource_config)

# Get a registered configuration
config = resource_config_registry.get("default")

# Thread-local override for a specific context
with resource_config_registry.override("test", test_resource_config):
    # Within this context, "test" config is used
    config = resource_config_registry.get("test")
```

## Resource Configuration in Nodes

Nodes, particularly `AIModelNode`, use resources for execution:

```python
from dhenara.agent.dsl import AIModelNode
from dhenara.ai.types import ResourceConfigItem

# Create a node with specific resource requirements
ai_node = AIModelNode(
    resources=ResourceConfigItem.with_model("claude-3-5-sonnet"),
    # Other settings...
)

# Or use multiple models
ai_node = AIModelNode(
    resources=ResourceConfigItem.with_models(["claude-3-5-sonnet", "gpt-4-turbo"]),
    # Other settings...
)
```

The `ResourceConfigItem` specifies what resources the node needs to execute.

## AI Model Configuration

AI models are a specific type of resource managed by DAD:

```python
from dhenara.ai.types import AIModel, AIModelCallConfig

# Define a model configuration
model = AIModel(
    model_id="claude-3-5-sonnet",
    provider="anthropic",
    api_key="${ANTHROPIC_API_KEY}",  # Environment variable reference
    endpoint="https://api.anthropic.com/v1/messages",
    default_call_config=AIModelCallConfig(
        temperature=0.7,
        max_tokens=4000,
        top_p=0.9,
    ),
)

# Register the model
model_registry.register("claude-3-5-sonnet", model)
```

## Credential Management

DAD provides several ways to manage credentials:

1. **Configuration Files**: YAML files with API keys and endpoints
2. **Environment Variables**: References using `${ENV_VAR_NAME}` syntax
3. **Runtime Configuration**: Programmatic configuration at startup

Example credentials file:

```yaml
# ~/.dhenara/credentials.yaml
api_keys:
  openai: ${OPENAI_API_KEY}
  anthropic: ${ANTHROPIC_API_KEY}
  google: ${GOOGLE_API_KEY}

endpoints:
  openai: "https://api.openai.com/v1"
  anthropic: "https://api.anthropic.com/v1"
  google: "https://generativelanguage.googleapis.com/v1"

resource_paths:
  models: "~/.dhenara/models"
```

## Resource Resolution

When a node requires resources, DAD resolves them in this order:

1. Thread-local override in the registry
2. Global registry entry
3. Default resource configuration

This allows for flexible configuration at different levels:

```python
# Global level - applies to all runs by default
resource_config_registry.register("default", default_resource_config)

# Run level - specific to a single run
run_context.resource_config = custom_resource_config

# Node level - specific to a single node
node = AIModelNode(
    resources=ResourceConfigItem.with_model("specific-model-config"),
    # Other settings...
)
```

## Resource Profiles

DAD supports the concept of resource profiles for different environments:

```python
# Get a specific resource profile
dev_config = run_context.get_resource_config("development")
staging_config = run_context.get_resource_config("staging")
prod_config = run_context.get_resource_config("production")
```

This allows for different resource configurations in different environments while maintaining the same code.

## Best Practices

1. **Use Environment Variables**: Store sensitive credentials as environment variables, not hardcoded values
2. **Resource Profiles**: Create separate resource profiles for different environments (dev, test, prod)
3. **Default Fallbacks**: Configure sensible defaults for resources
4. **Thread Isolation**: Use thread-local overrides for parallel execution with different resources
5. **Resource Validation**: Validate resources are available before execution begins

By following these practices and using DAD's resource management system, you can create flexible, secure agent workflows that can work across different environments and with multiple AI providers.
