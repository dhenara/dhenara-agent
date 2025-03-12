# Flow Definition in DAD Architecture

## Overview

The Flow Definition is a core component of the Dhenara Agent Definition (DAD) Architecture. It provides a structured way to define AI agent behaviors, interactions, and execution patterns.

## Flow Structure

A flow consists of three main components:

```json
{
  "name": "Flow Name",
  "description": "Flow Description",
  "definition": {
    // Flow definition contents
  }
}
```

### Core Components

1. **Flow Node**: Basic operational unit containing:

   - Unique identifier
   - Operation type
   - Execution order
   - Resource configurations
   - Input/Output settings

2. **Flow Definition**: Orchestrates multiple nodes:

   - Execution strategy
   - System-wide instructions
   - Node collection

3. **Settings Groups**:
   - AI Settings
   - Input Settings
   - Storage Settings
   - Response Settings

## Node Configuration

### Basic Node Structure

```json
{
  "order": 0,
  "identifier": "node_id",
  "type": "ai_model_call",
  "resources": [],
  "ai_settings": {},
  "input_settings": {},
  "storage_settings": {},
  "response_settings": {},
  "pre_actions": [],
  "post_actions": []
}
```

### Input Configuration

```json
{
  "input_settings": {
    "input_source": {
      "user_input_sources": ["full"],
      "node_output_sources": ["previous"]
    }
  }
}
```

### AI Settings

```json
{
  "ai_settings": {
    "system_instructions": ["Instruction 1", "Instruction 2"],
    "node_prompt": {
      "pre_prompt": ["Context:"],
      "prompt": ["Main prompt"],
      "post_prompt": ["Additional instructions"]
    },
    "options_overrides": {
      "temperature": 0.7
    }
  }
}
```

### Response Settings

```json
{
  "response_settings": {
    "enabled": true,
    "protocol": "http",
    "response_filters": [
      {
        "content_type": "full",
        "include_fields": ["output", "metadata"],
        "exclude_fields": ["internal_data"]
      }
    ]
  }
}
```

## Validation Rules

1. **Node Identifiers**:

   - Must be unique across the flow
   - Cannot use reserved identifiers
   - Must follow pattern: `^[a-zA-Z0-9_-]+$`

2. **Node Order**:

   - Must start from 0
   - Must be sequential
   - No gaps allowed

3. **Resources**:

   - At least one resource must be marked as default
   - Multiple resources allowed with one default

4. **Input Settings**:
   - Cannot mix direct prompts with user inputs
   - Must reference valid node identifiers

## Example Flow

```json
{
  "name": "Simple Chatbot",
  "description": "Basic chatbot with response generation",
  "definition": {
    "execution_strategy": "sequential",
    "system_instructions": ["Always be helpful"],
    "nodes": [
      {
        "order": 0,
        "identifier": "user_input",
        "type": "ai_model_call",
        "resources": [
          {
            "item_type": "ai_model_endpoint",
            "is_default": true
          }
        ],
        "input_settings": {
          "input_source": {
            "user_input_sources": ["full"]
          }
        },
        "response_settings": {
          "enabled": true,
          "protocol": "http"
        }
      }
    ]
  }
}
```

## Best Practices

1. Use meaningful node identifiers
2. Keep flows modular and focused
3. Validate flows before deployment
4. Document custom configurations
5. Use appropriate response protocols
6. Configure proper error handling

For detailed API reference and examples, visit our [documentation portal](https://docs.dhenara.io).
