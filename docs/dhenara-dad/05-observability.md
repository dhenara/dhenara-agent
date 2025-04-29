# Dhenara Agent DSL (DAD) - Observability

## Observability Overview

Observability is a core feature of DAD, providing comprehensive tracking, logging, and metrics for all agent activities. The observability system enables developers to understand, debug, and optimize their agent workflows with detailed visibility into execution.

## Core Observability Components

### 1. Tracing System

The tracing system tracks the execution path of components and nodes:

```python
from dhenara.agent.observability.tracing import setup_tracing, get_tracer, trace_method, trace_node

# Use decorators for automatic tracing
@trace_method("my_method")
async def my_method(self, param1):
    # Method implementation
    pass

@trace_node("my_custom_node_type")
async def execute_node(self, node_id, execution_context, node_input):
    # Node execution implementation
    pass
```

The tracing system creates hierarchical spans that capture:
- Execution path and hierarchies
- Timing information
- Input and output data
- Success/failure status
- Error information

### 2. Logging System

The logging system provides structured logging with context:

```python
from dhenara.agent.observability import log_with_context
import logging

# Log with trace context
log_with_context(
    logger,
    logging.INFO,
    "Processing completed successfully",
    {"items_processed": 42, "processing_time_ms": 1250}
)
```

This automatically associates logs with the current execution context and trace.

### 3. Metrics System

The metrics system collects numerical data about execution:

```python
from dhenara.agent.observability import record_metric

# Record a metric
record_metric(
    meter_name="dhenara.agent.processing",
    metric_name="items_processed",
    value=42,
    metric_type="counter",
    attributes={"node_id": "my_processor", "item_type": "document"}
)
```

Metrics can be aggregated and analyzed to monitor performance and behavior.

## Observability Configuration

Observability is configured through `ObservabilitySettings`:

```python
from dhenara.agent.observability.types import ObservabilitySettings
from dhenara.agent.observability import configure_observability
import logging

# Create settings
settings = ObservabilitySettings(
    service_name="my-agent-app",
    tracing_exporter_type="file",  # "console", "file", "otlp", "jaeger", "zipkin"
    metrics_exporter_type="file",
    logging_exporter_type="file",
    trace_file_path="/path/to/trace.jsonl",
    metrics_file_path="/path/to/metrics.jsonl",
    log_file_path="/path/to/logs.jsonl",
    root_log_level=logging.INFO,
)

# Apply configuration
configure_observability(settings)
```

The `RunContext` automatically configures observability based on run parameters.

## Tracing Profiles

Tracing profiles define what data should be captured in traces:

```python
from dhenara.agent.observability.tracing.data import (
    NodeTracingProfile,
    TracingDataField,
    TracingDataCategory,
)

# Define a tracing profile for a custom node
my_node_profile = NodeTracingProfile(
    node_type="my_custom_node",
    input_fields=[
        TracingDataField(
            name="query",
            source_path="query",
            category=TracingDataCategory.primary,
            max_length=500,
            description="The search query",
        ),
        # More fields...
    ],
    output_fields=[
        # Output fields...
    ],
    result_fields=[
        # Result fields...
    ],
)
```

Profiles help control what data is captured in traces, balancing detail against volume.

## Exporters

DAD supports multiple exporters for observability data:

- **Console**: Output to console (good for development)
- **File**: JSON line format files (default)
- **OTLP**: OpenTelemetry Protocol (for integration with observability platforms)
- **Jaeger**: Direct export to Jaeger tracing
- **Zipkin**: Direct export to Zipkin tracing

```python
# Configure for Jaeger export
settings = ObservabilitySettings(
    service_name="my-agent-app",
    tracing_exporter_type="jaeger",
    jaeger_endpoint="http://localhost:14268/api/traces",
)
```

## Dashboards

DAD includes built-in dashboard support for visualizing traces:

```python
from dhenara.agent.observability.dashboards import (
    run_dashboard,
    run_jaeger_dashboard,
    run_zipkin_dashboard,
)

# Run a simple dashboard on a trace file
run_dashboard("path/to/trace.jsonl", port=8080)

# Or launch Jaeger in a Docker container
run_jaeger_dashboard()
```

## Trace Decorators

The two primary trace decorators are:

1. `trace_method` - For general method tracing:
   ```python
   @trace_method(
       name="process_data",
       capture_args=["data_id", "options"],
       capture_result=True
   )
   def process_data(self, data_id, options, context):
       # Implementation
   ```

2. `trace_node` - Specifically for node execution:
   ```python
   @trace_node("my_node_type", profile=my_tracing_profile)
   async def execute(self, node_id, execution_context, node_input):
       # Implementation
   ```

## Best Practices

1. **Hierarchical Context**: Ensure proper nesting of traces through the component hierarchy
2. **Selective Tracing**: Be strategic about what data to capture, especially for large inputs/outputs
3. **Structured Logging**: Use log_with_context to maintain correlation with traces
4. **Meaningful Metrics**: Capture metrics that provide insights into performance and behavior
5. **Regular Analysis**: Use the dashboard tools to analyze execution and identify improvements

By utilizing DAD's observability features, developers can gain deep insights into their agent systems, diagnose issues more effectively, and optimize performance.
