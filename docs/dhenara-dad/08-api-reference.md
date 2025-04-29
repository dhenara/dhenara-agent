# Dhenara Agent DSL (DAD) - API Reference

## Core Components

### FlowDefinition

```python
class FlowDefinition(ComponentDefinition):
    def __init__(self, *, root_id: Optional[str] = None):
        """Initialize a flow definition.
        
        Args:
            root_id: Optional identifier for the root flow.
        """
        
    def node(self, node_id: str, node_definition: NodeDefinition) -> "FlowDefinition":
        """Add a node to the flow.
        
        Args:
            node_id: Unique identifier for the node within this flow
            node_definition: The node definition object
            
        Returns:
            The flow definition for method chaining
        """
        
    def connect(self, 
                source_id: str, 
                target_id: str, 
                on_success: bool = True, 
                on_error: bool = False) -> "FlowDefinition":
        """Connect nodes in the flow.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            on_success: Connect on successful execution of source
            on_error: Connect on error in source execution
            
        Returns:
            The flow definition for method chaining
        """
        
    def sequence(self, node_ids: list[str]) -> "FlowDefinition":
        """Create a sequential connection between nodes.
        
        Args:
            node_ids: List of node IDs to connect in sequence
            
        Returns:
            The flow definition for method chaining
        """
```

### AgentDefinition

```python
class AgentDefinition(ComponentDefinition):
    def __init__(self, *, root_id: Optional[str] = None):
        """Initialize an agent definition.
        
        Args:
            root_id: Optional identifier for the root agent.
        """
        
    def flow(self, flow_id: str, flow_definition: FlowDefinition) -> "AgentDefinition":
        """Add a flow to the agent.
        
        Args:
            flow_id: Unique identifier for the flow within this agent
            flow_definition: The flow definition object
            
        Returns:
            The agent definition for method chaining
        """
        
    def sequence(self, flow_ids: list[str]) -> "AgentDefinition":
        """Create a sequential connection between flows.
        
        Args:
            flow_ids: List of flow IDs to connect in sequence
            
        Returns:
            The agent definition for method chaining
        """
        
    def condition(self, 
                  flow_id: str, 
                  condition_fn: Callable[[ExecutionContext], bool]) -> "AgentDefinition":
        """Add a condition for flow execution.
        
        Args:
            flow_id: ID of the flow to condition
            condition_fn: Function that returns True if flow should execute
            
        Returns:
            The agent definition for method chaining
        """
```

## Node Components

### AIModelNode

```python
class AIModelNode(NodeDefinition):
    def __init__(self, 
                resources: ResourceConfigItem,
                settings: Optional[AIModelNodeSettings] = None,
                pre_events: Optional[list[EventType]] = None,
                post_events: Optional[list[EventType]] = None):
        """Initialize an AI model node.
        
        Args:
            resources: Resource configuration for the AI model
            settings: Settings for the AI model node
            pre_events: Events to process before node execution
            post_events: Events to emit after node execution
        """
```

### AIModelNodeSettings

```python
class AIModelNodeSettings(NodeSettings):
    system_instructions: list[str] = Field(default_factory=list)
    prompt: Optional[Prompt] = None
    model_call_config: Optional[AIModelCallConfig] = None
    record_settings: Optional[NodeRecordSettings] = None
```

### FileOperationNode

```python
class FileOperationNode(NodeDefinition):
    def __init__(self, 
                settings: Optional[FileOperationNodeSettings] = None,
                pre_events: Optional[list[EventType]] = None,
                post_events: Optional[list[EventType]] = None):
        """Initialize a file operation node.
        
        Args:
            settings: Settings for the file operation node
            pre_events: Events to process before node execution
            post_events: Events to emit after node execution
        """
```

### FolderAnalyzerNode

```python
class FolderAnalyzerNode(NodeDefinition):
    def __init__(self, 
                settings: Optional[FolderAnalyzerSettings] = None,
                pre_events: Optional[list[EventType]] = None,
                post_events: Optional[list[EventType]] = None):
        """Initialize a folder analyzer node.
        
        Args:
            settings: Settings for the folder analyzer node
            pre_events: Events to process before node execution
            post_events: Events to emit after node execution
        """
```

## Runner Components

### FlowRunner

```python
class FlowRunner(ComponentRunner):
    def __init__(self, 
                component_def: FlowDefinition, 
                run_context: RunContext, 
                root_id: Optional[str] = None):
        """Initialize a flow runner.
        
        Args:
            component_def: The flow definition to run
            run_context: The run context for execution
            root_id: Optional root ID (defaults to flow's root_id)
        """
        
    def setup_run(self, 
                previous_run_id: Optional[str] = None,
                start_hierarchy_path: Optional[str] = None,
                run_id_prefix: Optional[str] = None):
        """Set up the run environment.
        
        Args:
            previous_run_id: Optional ID of a previous run to continue from
            start_hierarchy_path: Optional hierarchy path to start from
            run_id_prefix: Optional prefix for the run ID
        """
        
    async def run(self) -> bool:
        """Execute the flow.
        
        Returns:
            True if execution was successful, False otherwise
        """
```

### AgentRunner

```python
class AgentRunner(ComponentRunner):
    def __init__(self, 
                component_def: AgentDefinition, 
                run_context: RunContext, 
                root_id: Optional[str] = None):
        """Initialize an agent runner.
        
        Args:
            component_def: The agent definition to run
            run_context: The run context for execution
            root_id: Optional root ID (defaults to agent's root_id)
        """
        
    def setup_run(self, 
                previous_run_id: Optional[str] = None,
                start_hierarchy_path: Optional[str] = None,
                run_id_prefix: Optional[str] = None):
        """Set up the run environment.
        
        Args:
            previous_run_id: Optional ID of a previous run to continue from
            start_hierarchy_path: Optional hierarchy path to start from
            run_id_prefix: Optional prefix for the run ID
        """
        
    async def run(self) -> bool:
        """Execute the agent.
        
        Returns:
            True if execution was successful, False otherwise
        """
```

## Run Context Components

### RunContext

```python
class RunContext:
    def __init__(self,
                root_component_id: str,
                project_root: Path,
                run_root: Optional[Path] = None,
                run_id: Optional[str] = None,
                observability_settings: Optional[ObservabilitySettings] = None,
                previous_run_id: Optional[str] = None,
                start_hierarchy_path: Optional[str] = None,
                input_source: Optional[Path] = None):
        """Initialize a run context.
        
        Args:
            root_component_id: ID of the root component being executed
            project_root: Root directory of the project
            run_root: Directory for run artifacts (defaults to project_root/runs)
            run_id: Optional ID for the run (auto-generated if None)
            observability_settings: Optional custom observability settings
            previous_run_id: Optional ID of a previous run to continue from
            start_hierarchy_path: Optional hierarchy path to start from
            input_source: Optional directory containing input files
        """
        
    def setup_run(self, run_id_prefix: Optional[str] = None):
        """Set up the run environment.
        
        Args:
            run_id_prefix: Optional prefix for the run ID
        """
        
    def register_node_static_input(self, node_id: str, input_data: NodeInput):
        """Register static input for a node.
        
        Args:
            node_id: ID of the node to provide input for
            input_data: The input data for the node
        """
        
    def register_node_input_handler(self, handler: Callable):
        """Register a handler for node input required events.
        
        Args:
            handler: Event handler function
        """
        
    def complete_run(self, status="completed", error_msg: Optional[str] = None):
        """Complete the run with specified status.
        
        Args:
            status: Status of the run ("completed" or "failed")
            error_msg: Optional error message if run failed
        """
```

## Observability Components

### ObservabilitySettings

```python
class ObservabilitySettings(BaseModel):
    service_name: str = "dhenara-dad"
    tracing_exporter_type: str = "file"  # "console", "file", "otlp", "jaeger", "zipkin"
    metrics_exporter_type: str = "file"  # "console", "file", "otlp"
    logging_exporter_type: str = "file"  # "console", "file", "otlp"
    otlp_endpoint: Optional[str] = None
    jaeger_endpoint: Optional[str] = "http://localhost:14268/api/traces"
    zipkin_endpoint: Optional[str] = "http://localhost:9411/api/v2/spans"
    root_log_level: int = logging.INFO
    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    trace_file_path: Optional[str] = None
    metrics_file_path: Optional[str] = None
    log_file_path: Optional[str] = None
    observability_logger_name: str = "dhenara.dad.observability"
    trace_log_level: int = logging.WARNING
```

## Resource Components

### ResourceConfigItem

```python
class ResourceConfigItem(BaseModel):
    model_id: Optional[str] = None
    model_ids: Optional[list[str]] = None
    
    @classmethod
    def with_model(cls, model_id: str) -> "ResourceConfigItem":
        """Create a resource config with a single model.
        
        Args:
            model_id: ID of the AI model to use
            
        Returns:
            ResourceConfigItem configured with the specified model
        """
        
    @classmethod
    def with_models(cls, model_ids: list[str]) -> "ResourceConfigItem":
        """Create a resource config with multiple models.
        
        Args:
            model_ids: List of model IDs to try in order
            
        Returns:
            ResourceConfigItem configured with the specified models
        """
```

This API reference covers the main components of DAD. For complete details on all classes and methods, please refer to the source code and inline documentation.
