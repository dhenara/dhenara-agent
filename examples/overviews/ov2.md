──────────────────────────────
Project Structure Overview
──────────────────────────────
• Root of package
  – setup.py: Standard setuptools configuration for the “dhenara-agent” package with dependencies (e.g. click, pyyaml, dhenara, opentelemetry packages, etc.)
  – examples/
    ◦ chatbot_with_summarizer.py
    ◦ chatbot_with_summarizer_using_ctx_source.py
    ◦ singleshot_coder.py
  – cli/
    ◦ Contains CLI commands (create, deploy, outputs, run, startproject) and related templates

──────────────────────────────
src/dhenara/ (Main source code)
──────────────────────────────

1. agent/
  • __init__.py: Exports core agent functionality.
  • client/
    – _base.py, _client.py, _stream.py, _urls.py
    – types subfolder: Contains Pydantic decorators (e.g. pydantic_endpoint) and functional types that wrap API responses.
  • config/
    – _config.py and __init__.py: Global configuration and context management.
  • dsl/ (Domain-Specific Language for agent/flow definitions)
    – base/
      ▸ __init__.py, component (comp_exe_result.py, component_def.py, executor.py), context.py, control.py
      ▸ data/ – Contains engines and parsers (dad_template_engine.py, expression_parser.py, template_engine.py)
      ▸ defs.py – Simple types and definitions (e.g. NodeID)
      ▸ element.py – Base “executable element” abstractions
      ▸ enums.py – Common enums (e.g. ExecutionStatusEnum, SpecialNodeIDEnum)
      ▸ node/ – Definition files for nodes including:
       • _executor_registry.py (registry for node executors)
       • node_block_ref.py (wrappers for executable nodes and block references)
       • node_def.py (base node definitions and load-from-previous-run methods)
       • node_exe_result.py (execution result models using Pydantic)
       • node_executor.py (abstract NodeExecutor with event triggering for missing inputs)
       • node_io.py (models for NodeInput/Output and custom dict subclass for inputs)
       • node_settings.py (record settings and git settings for node outputs)
    – components/
     ◦ agent/
      ▸ Contains AgentNode, AgentExecutionContext, AgentNodeDefinition, AgentNodeExecutor, and a legacy “todo_old_agent_node”
     ◦ flow/
      ▸ Contains FlowElement, FlowNode, FlowExecutionContext, FlowNodeDefinition, FlowNodeExecutor, and flow-level executors/components
    – events/
     ◦ event.py – Defines BaseEvent, NodeInputRequiredEvent with timestamp and handling flags
     ◦ event_bus.py – Simple event bus that supports register/ wildcard and publishes events (nodes, flows) with different natures (notify, with_wait, with_future)
    – inbuilt/
     ◦ agent_nodes/
      ▸ basic_agent/ – Implements a basic agent node: input.py, node.py, output.py, settings.py, tracing.py
      ▸ coordinator_agent/ – Contains a sample temporary coordinator agent (_temp.py)
      ▸ defs/ – Contains built-in enums for agent nodes
     ◦ flow_nodes/
      ▸ ai_model/ – Implements nodes for calling AI models with files: executor.py, input.py, node.py, output.py, settings.py, tracing.py
      ▸ command/ – Implements nodes to execute shell commands (executor.py, input.py, node.py, output.py, settings.py, tracing.py)
      ▸ file_operation/ – Implements file operations (read, write, edit, create directory, delete, move, etc.) with corresponding executor, input, node, output, settings, tracing.
      ▸ folder_analyzer/ – Implements methods to scan folders: helper functions (python_extractor.py, helper_fns.py), executor.py, input.py, node.py, output.py, settings.py, tracing.py
      ▸ legacy_handlers/ – Contains custom, git_command, git_repo_analyzer, rag_index, rag_query modules
     ◦ registry/
      ▸ __init__.py, trace_registry.py – Global registry for registering built-in tracing profiles

2. memory_management/
  • Contains modules for short-term and long-term memory handling, shared memory, and placeholders for memory backends (e.g. Redis, SQLite, Pinecone)

3. observability/
  • __init__.py
  • cli/ – Dashboard commands (dashboard.py) to view traces (console, Jaeger, Zipkin)
  • config.py – Centralized configuration function (configure_observability) and access getters
  • dashboards/ – Includes dashboards backed by Docker (jaeger, zipkin, grafana, custom dashboards)
  • exporters/ – Custom exporters for logs, metrics, and spans (file exporters, Jaeger and Zipkin exporters)
  • logging.py – Setup for logging incorporating opentelemetry and additional trace log handler
  • metrics.py – Setup for metrics with OpenTelemetry exporters
  • tracing/
    – data/ – Tracing data definitions, node tracing profiles, profile registry
    – decorators/ – Decorators to wrap functions/methods for tracing (_fns.py, _fns2.py)
    – tracing.py – Setup of tracing exporters (jaeger, zipkin, otlp, file) and tracer getters
    – tracing_log_handler.py – Custom log handler to inject log information into spans
    – profile.py – Definitions of NodeTracingProfile, TracingDataField, TracingDataCategory
  • types/ – Observability settings model (ObservabilitySettings)
  • Other modules: context for observability context, shared utilities

4. run/
  • __init__.py
  • isolated_execution.py – Provides a context manager for isolated agent execution (sets/changers environment and working directory)
  • registry/
    – _resource_registry.py and registry.py – Thread-safe registries for shared resources, e.g. models and resource configurations
  • run_context.py – Manages a single execution run: setup_run (run_id, directories, outcome repo, trace_dir), copying static inputs, registering node inputs and storing outputs
  • workspace.py – Manages a temporary workspace for cloning repositories, file IO, and cleaning up temporary files

5. runner/
  • __init__.py, registry.py, runner.py – Core entry point for running agents and flows; defines ComponentRunner, AgentRunner, FlowRunner classes that wrap execution context and complete run lifecycle with logging, metrics, git outcomes, and error handling

6. shared/
  • utils/ – Common utilities (e.g. _project.py: functions to derive project configuration, project root detection)

7. tool/
  • Contains tool registry, API connectors (e.g. api_connectors.py, file_io.py, math_or_code_execution.py, knowledge_base_query.py, web_search.py) and a standardized interface

8. types/
  • base/: BaseModel and BaseEnum definitions (e.g. _base_type.py)
  • data/: Data models for run environment (_run_env.py)
  • platform/: Platform exceptions and error types (_exceptions.py)

9. utils/
  • git/ – Utility modules to interact with Git, such as:
    – gitbase.py (core git operations),
    – outcome_repository.py (manages git repo for agent outcomes),
    – repo_analyzer.py (analyzes repo structure and metadata)
  • io/ – File and artifact management (artifact_manager.py, artifact_manager_improved.py, file_io_base.py)

──────────────────────────────
CLI (Command Line Interface)
──────────────────────────────
• Located under dhenagent/cli/
  – commands: create.py (for new agent/project creation), deploy.py, outputs.py, run.py, startproject.py
  – main.py: The entry point that imports and registers all CLI commands dynamically from both “cli” and observability modules

──────────────────────────────
Key Themes and Features
──────────────────────────────
• DSL for defining agents and flows
  – Supports hierarchical node definitions, reusable components, conditional branches, and loops (ForEach, Conditional)
  – Provides type‐safe Pydantic models for inputs, outputs, outcomes, and settings
• Observability integrated across execution
  – Setup for logging, metrics, and distributed tracing using OpenTelemetry
  – Custom exporters and tracing decorators (trace_method, trace_node)
  – Registries for built‐in tracing profiles
• Resource Management and Git Integration
  – RunContext handles temporary workspace, static inputs, copying files and managing outcomes
  – Git utilities to clone repos, commit outcomes, compare run histories
• Templating and Expression Evaluation
  – DADTemplateEngine extends a base TemplateEngine to substitute variables (“$var{}”) and evaluate expressions (“$expr{}”)
  – Supports dynamic variables from run environment and node execution results
• Extensibility
  – Registries for resources, node executors, tools, and tracing profiles
  – Modular structure with clear separation between DSL definitions, execution runners, and CLI commands

──────────────────────────────
Usage Scenarios
──────────────────────────────
• Agent creation and execution
  – Define an agent using DSL (e.g. AIModelNode in a flow) and run it either via CLI (“dhenara run agent <id>”) or isolated execution
• Code modification or utility operations
  – Built-in nodes for file operations, folder analysis, command execution
• Observability and tracing
  – Integrated dashboards (Jaeger, Zipkin, console) to review metrics and trace logs
• Project scaffolding
  – “startproject” and “create agent” CLI commands create a structured project with default configuration, git initialization, and template files

──────────────────────────────
Summary
──────────────────────────────
The dhenagent project is a comprehensive, modular framework atop the dhenara package that provides a DSL for AI agent and flow development. Its architecture splits functionality into distinct layers:
  – DSL definitions for nodes, flows, and components (with built‐in support for agents, file operations, folder analysis, and commands),
  – Observability (logging, metrics, tracing, dashboards),
  – Resource and run management (workspace creation, git outcome repository, execution context), and
  – A CLI interface to create, run, deploy, and compare agent executions.
Each module uses modern Python (>3.10) type hints and Pydantic models ensuring a type‐safe, extensible, and professional agent creation ecosystem.
