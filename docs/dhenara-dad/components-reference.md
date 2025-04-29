# Dhenara Agent DSL (DAD) Components Reference

## Overview

This document provides a detailed reference for the built-in components in Dhenara Agent DSL (DAD). It covers nodes, flows, agents, and their supporting classes, explaining their purpose, properties, and usage patterns.

## Node Components

Nodes are the atomic execution units in Dhenara Agent DSL (DAD). Each node type serves a specific purpose and can be configured for different behaviors.

### AIModelNode

Makes calls to AI models, handling prompts, contexts, and responses.

```python
class AIModelNode(FlowNodeDefinition):
    node_type: str = FlowNodeTypeEnum.ai_model_call
    settings: AIModelNodeSettings | None
    resources: list[ResourceConfigItem]
    tools: list
```

**Key Properties:**

- **settings**: Configuration for the node, including prompts and system instructions
- **resources**: List of AI model resources that can be used by the node
- **tools**: Tools that can be provided to the model (for tool-using models)
- **pre_events**: Events that occur before node execution (e.g., for input requirements)

**Settings Class:**

```python
class AIModelNodeSettings(NodeSettings):
    prompt: Prompt | None
    context: list[Prompt] | None
    context_sources: list[str] | None
    system_instructions: list[str | SystemInstruction] | None
    model_call_config: AIModelCallConfig | None
```

**Input Class:**

```python
class AIModelNodeInput(NodeInput):
    prompt_variables: dict[str, Any]
    instruction_variables: dict[str, Any]
    settings_override: AIModelNodeSettings | None
    resources_override: list[ResourceConfigItem]
```

**Output Classes:**

```python
class AIModelNodeOutputData(BaseModel):
    response: AIModelCallResponse | None

class AIModelNodeOutput(NodeOutput[AIModelNodeOutputData]):
    pass

class AIModelNodeOutcome(NodeOutcome):
    text: str | None
    structured: dict | None
    file: GenericFile | None
    files: list[GenericFile] | None
```

**Example Usage:**

```python
AIModelNode(
    resources=ResourceConfigItem.with_models("claude-3-opus"),
    pre_events=[EventType.node_input_required],
    settings=AIModelNodeSettings(
        system_instructions=["You are a helpful coding assistant."],
        prompt=Prompt.with_text("Generate a function that $var{task}"),
        model_call_config=AIModelCallConfig(
            structured_output=TaskImplementation,
            max_output_tokens=8000,
        )
    )
)
```

### FileOperationNode

Performs file operations such as creating, editing, deleting, and moving files.

```python
class FileOperationNode(FlowNodeDefinition):
    node_type: str = FlowNodeTypeEnum.file_operation
    settings: FileOperationNodeSettings | None
```

**Key Properties:**

- **settings**: Configuration for the node, including the base directory and operations to perform

**Settings Class:**

```python
class FileOperationNodeSettings(NodeSettings):
    base_directory: str
    operations_template: ObjectTemplate
    stage: bool
    commit: bool
    commit_message: str | None
```

**Input Class:**

```python
class FileOperationNodeInput(NodeInput):
    settings_override: FileOperationNodeSettings | None
    operations: list[FileOperation] | None
```

**Example Usage:**

```python
FileOperationNode(
    settings=FileOperationNodeSettings(
        base_directory="/path/to/project",
        operations_template=ObjectTemplate(
            expression="$hier{code_generator}.outcome.structured.file_operations"
        ),
        stage=True,
        commit=True,
        commit_message="Implemented feature X"
    )
)
```

### FolderAnalyzerNode

Analyzes folder structures and extracts information from files.

```python
class FolderAnalyzerNode(FlowNodeDefinition):
    node_type: str = FlowNodeTypeEnum.folder_analyzer
    settings: FolderAnalyzerSettings | None
```

**Key Properties:**

- **settings**: Configuration for the node, including the base directory and operations to perform

**Settings Class:**

```python
class FolderAnalyzerSettings(NodeSettings):
    base_directory: str
    operations: list[FolderAnalysisOperation]
    include_content: bool
```

**Input Class:**

```python
class FolderAnalyzerNodeInput(NodeInput):
    settings_override: FolderAnalyzerSettings | None
    operations: list[FolderAnalysisOperation] | None
```

**Example Usage:**

```python
FolderAnalyzerNode(
    settings=FolderAnalyzerSettings(
        base_directory="/path/to/project",
        operations=[
            FolderAnalysisOperation(
                operation_type="analyze_folder",
                path="src",
                include_patterns=["*.py"],
                exclude_patterns=["__pycache__"],
                include_content=True
            )
        ]
    )
)
```

### CommandNode

Executes shell commands and captures outputs.

```python
class CommandNode(FlowNodeDefinition):
    node_type: str = FlowNodeTypeEnum.command
    settings: CommandNodeSettings | None
```

**Key Properties:**

- **settings**: Configuration for the node, including the command to run and the working directory

**Settings Class:**

```python
class CommandNodeSettings(NodeSettings):
    command: str | list[str]
    working_directory: str | None
    environment: dict[str, str] | None
    timeout: int | None
```

**Example Usage:**

```python
CommandNode(
    settings=CommandNodeSettings(
        command=["git", "status"],
        working_directory="/path/to/project",
        timeout=30
    )
)
```

## Flow Components

Flows combine nodes into sequences, conditionals, and loops, defining the execution logic of an agent.

### FlowDefinition

Defines a flow of nodes and subflows with execution logic.

```python
class FlowDefinition(ComponentDefinition[FlowExecutionContext, FlowExecutionResult]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.flow
    context_class = FlowExecutionContext
    result_class = FlowExecutionResult
```

**Key Methods:**

- **node**: Add a node to the flow
- **subflow**: Add a subflow to the flow
- **conditional**: Add a conditional branch to the flow
- **for_each**: Add a loop to the flow

**Example Usage:**

```python
my_flow = FlowDefinition()
my_flow.node("analyzer", analyzer_node)
my_flow.node("processor", processor_node)

# Add a conditional branch
my_flow.conditional(
    "condition_check",
    statement=ObjectTemplate(expression="$hier{analyzer}.outcome.structured.file_count > 0"),
    true_branch=process_branch,
    false_branch=empty_branch
)

# Add a loop
my_flow.for_each(
    "process_files",
    statement=ObjectTemplate(expression="$hier{analyzer}.outcome.structured.files"),
    body=file_processor,
    max_iterations=100
)
```

### Flow

Represents an executable flow instance.

```python
class Flow(ExecutableComponent[FlowDefinition, FlowExecutionContext]):
    id: NodeID
    definition: FlowDefinition
```

**Key Methods:**

- **execute**: Execute the flow with a given execution context

## Agent Components

Agents are the top-level components that represent complete functional units.

### AgentDefinition

Defines an agent with flows and subagents.

```python
class AgentDefinition(ComponentDefinition[AgentExecutionContext, AgentExecutionResult]):
    executable_type: ExecutableTypeEnum = ExecutableTypeEnum.agent
    context_class = AgentExecutionContext
    result_class = AgentExecutionResult
```

**Key Methods:**

- **flow**: Add a flow to the agent
- **subagent**: Add a subagent to the agent
- **conditional**: Add a conditional branch to the agent
- **for_each**: Add a loop to the agent

**Example Usage:**

```python
my_agent = AgentDefinition()
my_agent.flow("main_flow", main_flow)
my_agent.subagent("helper_agent", helper_agent)

# Add a conditional branch
my_agent.conditional(
    "condition_check",
    statement=ObjectTemplate(expression="$hier{main_flow.analyzer}.outcome.structured.requires_helper"),
    true_branch=helper_branch,
    false_branch=direct_branch
)
```

### Agent

Represents an executable agent instance.

```python
class Agent(ExecutableComponent[AgentDefinition, AgentExecutionContext]):
    id: NodeID
    definition: AgentDefinition
```

**Key Methods:**

- **execute**: Execute the agent with a given execution context

## Common Components

### ExecutionContext

Manages state during execution.

```python
class ExecutionContext(BaseModelABC):
    executable_type: ExecutableTypeEnum
    control_block_type: ControlBlockTypeEnum | None
    component_id: NodeID
    component_definition: Any
    context_id: uuid.UUID
    parent: Optional["ExecutionContext"]
    execution_status: ExecutionStatusEnum
    execution_results: dict[NodeID, NodeExecutionResult]
    run_context: RunContext
```

**Key Methods:**

- **get_hierarchy_path**: Get the hierarchical path of the context
- **set_result**: Set the result of a node execution
- **get_context_variables_hierarchical**: Get variables from the context hierarchy

### EventBus

Manages events and event handlers.

```python
class EventBus:
    def register(self, event_type: EventType, handler: Callable): ...
    def register_wildcard(self, handler: Callable): ...
    async def publish(self, event: BaseEvent): ...
```

**Key Methods:**

- **register**: Register a handler for a specific event type
- **register_wildcard**: Register a handler for all event types
- **publish**: Publish an event to all registered handlers

### TemplateEngine

Processes templates, expressions, and references.

```python
class TemplateEngine:
    @classmethod
    def render_template(cls, template: str, variables: dict[str, Any], execution_context: Optional["ExecutionContext"] = None, mode: Literal["standard", "expression"] = "expression", max_words: int | None = None, debug_mode: bool = False) -> str: ...

    @classmethod
    def evaluate_template(cls, expr_template: str, variables: dict[str, Any], execution_context: Optional["ExecutionContext"] = None, debug_mode: bool = False) -> Any: ...
```

**Key Methods:**

- **render_template**: Render a template with variable substitution and expression evaluation
- **evaluate_template**: Evaluate an expression within a template

### DADTemplateEngine

Extends the TemplateEngine with DAD-specific functionality.

```python
class DADTemplateEngine(TemplateEngine):
    @classmethod
    def render_dad_template(cls, template: str | Prompt | TextTemplate | ObjectTemplate, variables: dict[str, Any], execution_context: ExecutionContext, mode: Literal["standard", "expression"] = "expression", max_words: int | None = None, max_words_file: int | None = None, debug_mode: bool = False, **kwargs: Any) -> Any: ...
```

**Key Methods:**

- **render_dad_template**: Render a DAD-specific template (Prompt, TextTemplate, ObjectTemplate, etc.)

## Utility Components

### ResourceConfigItem

Defines a resource that can be used by a node.

```python
class ResourceConfigItem:
    item_type: str
    provider: str
    is_default: bool
    query: Any
```

**Factory Methods:**

- **with_models**: Create a resource config item for specific models
- **with_model**: Create a resource config item for a single model

### Prompt

Defines a prompt for an AI model.

```python
class Prompt:
    text: str | PromptText
    variables: dict[str, Any]
    metadata: dict[str, Any] | None
```

**Factory Methods:**

- **with_text**: Create a prompt with a text string
- **with_dad_text**: Create a prompt with a DAD template text

### ObjectTemplate

Defines a template that evaluates to an object.

```python
class ObjectTemplate:
    expression: str
```

**Example Usage:**

```python
ObjectTemplate(expression="$hier{analyzer}.outcome.structured.files")
```

### SystemInstruction

Defines a system instruction for an AI model.

```python
class SystemInstruction:
    text: str
    variables: dict[str, Any]
```

**Example Usage:**

```python
SystemInstruction(
    text="You are a $var{role} that specializes in $var{specialty}.",
    variables={"role": "coding assistant", "specialty": "Python"}
)
```
