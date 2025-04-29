# Dhenara Agent DSL (DAD): Practical Examples

## Introduction

This document provides practical examples of how to use Dhenara Agent DSL (DAD) for different use cases. Each example demonstrates a specific pattern or approach, with explanations of key concepts and techniques.

## Example 1: Basic Code Generation Agent

This example demonstrates a simple agent that analyzes a repository, generates code based on requirements, and implements the changes.

```python
from dhenara.agent.dsl import (
    AIModelNode,
    AIModelNodeSettings,
    EventType,
    FileOperationNode,
    FileOperationNodeSettings,
    FlowDefinition,
    FolderAnalyzerNode,
    FolderAnalyzerSettings,
)
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import FolderAnalysisOperation
from dhenara.ai.types import (
    AIModelCallConfig,
    ObjectTemplate,
    Prompt,
    ResourceConfigItem,
)

from src.agents.autocoder.types import TaskImplementation

# Define repository directory
repo_dir = "/path/to/repository"

# Available models
models = [
    "claude-3-7-sonnet",
    "gpt-4.1-nano",
    "claude-3-5-haiku",
    "gemini-2.0-flash"
]

# Create a flow for implementing code changes
implementation_flow = FlowDefinition()

# Add a folder analyzer node to analyze the repository
implementation_flow.node(
    "repo_analysis",
    FolderAnalyzerNode(
        pre_events=[EventType.node_input_required],
        settings=FolderAnalyzerSettings(
            base_directory=repo_dir,
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
)

# Add an AI model node to generate code changes
implementation_flow.node(
    "code_generator",
    AIModelNode(
        resources=ResourceConfigItem.with_models("claude-3-7-sonnet"),
        pre_events=[EventType.node_input_required],
        settings=AIModelNodeSettings(
            system_instructions=[
                "You are a professional code implementation agent.",
                "Your task is to generate the exact file operations necessary to implement requested changes.",
            ],
            prompt=Prompt.with_dad_text(
                text=(
                    "Implement the following batch of code changes:\n\n"
                    "Task: $var{task_description} \n"
                    "Context Files info: $hier{repo_analysis}.outcome.structured\n\n"
                    "Return a TaskImplementation object."
                ),
            ),
            model_call_config=AIModelCallConfig(
                structured_output=TaskImplementation,
                max_output_tokens=8000,
            ),
        ),
    ),
)

# Add a file operation node to implement the changes
implementation_flow.node(
    "code_implementer",
    FileOperationNode(
        settings=FileOperationNodeSettings(
            base_directory=repo_dir,
            operations_template=ObjectTemplate(
                expression="$hier{code_generator}.outcome.structured.file_operations"
            ),
            stage=True,
            commit=True,
            commit_message="Implemented requested changes"
        )
    )
)

# Input handler for the nodes
async def handle_input_required(event: NodeInputRequiredEvent):
    if event.node_id == "repo_analysis":
        # Configure the folder analysis
        event.input = FolderAnalyzerNodeInput(
            settings_override=FolderAnalyzerSettings(
                base_directory=repo_dir,
                operations=[
                    FolderAnalysisOperation(
                        operation_type="analyze_folder",
                        path="src",
                        include_patterns=["*.py"],
                        exclude_patterns=["__pycache__, *.pyc"],
                        include_content=True
                    )
                ]
            )
        )
        event.handled = True
    elif event.node_id == "code_generator":
        # Get the model and task description from the user
        selected_model = await get_model_selection(models)
        task_description = await get_task_description()

        event.input = AIModelNodeInput(
            resources_override=[ResourceConfigItem.with_model(selected_model)],
            prompt_variables={
                "task_description": task_description
            }
        )
        event.handled = True

# Register the input handler
event_bus.register(EventType.node_input_required, handle_input_required)

# Execute the flow
result = await implementation_flow.execute(
    execution_context=FlowExecutionContext(
        component_id="implementation_flow",
        component_definition=implementation_flow,
        run_context=run_context
    )
)
```

**Key Concepts:**

1. **Repository Analysis**: The `FolderAnalyzerNode` examines the repository to provide context for the code generation.
2. **AI-Powered Code Generation**: The `AIModelNode` uses an LLM to generate structured code changes based on the repository analysis and task description.
3. **Code Implementation**: The `FileOperationNode` applies the generated changes to the repository.
4. **Interactive Input**: The input handler collects necessary inputs for each node, enabling user interaction.

## Example 2: Multi-Step Code Review Agent

This example shows a more complex agent that performs multi-step code reviews by first analyzing the code, then generating improvement suggestions, and finally implementing selected improvements.

```python
from dhenara.agent.dsl import (
    AgentDefinition,
    AIModelNode,
    AIModelNodeSettings,
    EventType,
    FileOperationNode,
    FileOperationNodeSettings,
    FlowDefinition,
    FolderAnalyzerNode,
    FolderAnalyzerSettings,
)
from dhenara.ai.types import (
    AIModelCallConfig,
    ObjectTemplate,
    Prompt,
    ResourceConfigItem,
)

from src.agents.code_review.types import CodeReview, CodeImprovements

# Create the code review agent
code_review_agent = AgentDefinition()

# 1. Analysis flow - analyze the code
analysis_flow = FlowDefinition()

# Add a folder analyzer node
analysis_flow.node(
    "repo_analysis",
    FolderAnalyzerNode(
        pre_events=[EventType.node_input_required],
        settings=FolderAnalyzerSettings(
            base_directory="$var{repo_dir}",
            operations=[
                FolderAnalysisOperation(
                    operation_type="analyze_folder",
                    path="$var{target_directory}",
                    include_patterns=["*.py"],
                    exclude_patterns=["__pycache__"],
                    include_content=True
                )
            ]
        )
    )
)

# Add a code analysis node
analysis_flow.node(
    "code_analyzer",
    AIModelNode(
        resources=ResourceConfigItem.with_models("claude-3-opus"),
        settings=AIModelNodeSettings(
            system_instructions=[
                "You are a code review expert. Analyze the provided code for issues and improvement opportunities."
            ],
            prompt=Prompt.with_dad_text(
                text=(
                    "Perform a detailed code review on the following files:\n\n"
                    "$hier{repo_analysis}.outcome.structured\n\n"
                    "Analyze for:\n"
                    "- Code quality issues\n"
                    "- Performance improvements\n"
                    "- Security concerns\n"
                    "- Best practices\n\n"
                    "Return a structured CodeReview object with your findings."
                ),
            ),
            model_call_config=AIModelCallConfig(
                structured_output=CodeReview,
                max_output_tokens=16000,
            ),
        ),
    ),
)

# 2. Improvement flow - generate improvement suggestions
improvement_flow = FlowDefinition()

improvement_flow.node(
    "improvement_generator",
    AIModelNode(
        resources=ResourceConfigItem.with_models("claude-3-opus"),
        pre_events=[EventType.node_input_required],
        settings=AIModelNodeSettings(
            system_instructions=[
                "You are a code improvement expert. Generate specific improvements based on code review findings."
            ],
            prompt=Prompt.with_dad_text(
                text=(
                    "Based on the code review findings, generate specific improvements for the following issues:\n\n"
                    "Code Review: $hier{analysis_flow.code_analyzer}.outcome.structured\n\n"
                    "For each selected issue, provide:\n"
                    "- Detailed explanation of the change\n"
                    "- Specific file operations to implement the change\n\n"
                    "Focus on: $var{improvement_focus}\n\n"
                    "Return a CodeImprovements object with your suggestions."
                ),
            ),
            model_call_config=AIModelCallConfig(
                structured_output=CodeImprovements,
                max_output_tokens=16000,
            ),
        ),
    ),
)

# 3. Implementation flow - implement selected improvements
implementation_flow = FlowDefinition()

implementation_flow.node(
    "improvement_implementer",
    FileOperationNode(
        pre_events=[EventType.node_input_required],
        settings=FileOperationNodeSettings(
            base_directory="$var{repo_dir}",
            operations_template=ObjectTemplate(
                expression="$var{selected_improvements}"
            ),
            stage=True,
            commit=True,
            commit_message="Implemented code improvements based on review"
        )
    )
)

# Add flows to the agent
code_review_agent.flow("analysis", analysis_flow)
code_review_agent.flow("improvement", improvement_flow)
code_review_agent.flow("implementation", implementation_flow)

# Input handlers
async def handle_input_required(event: NodeInputRequiredEvent):
    if event.node_id == "repo_analysis":
        # Get repository and target directory from user
        repo_dir = await get_repo_directory()
        target_directory = await get_target_directory()

        event.input = FolderAnalyzerNodeInput(
            settings_override=FolderAnalyzerSettings(
                base_directory=repo_dir,
                operations=[
                    FolderAnalysisOperation(
                        operation_type="analyze_folder",
                        path=target_directory,
                        include_patterns=["*.py"],
                        exclude_patterns=["__pycache__"],
                        include_content=True
                    )
                ]
            )
        )
        event.handled = True
    elif event.node_id == "improvement_generator":
        # Get improvement focus from user
        improvement_focus = await get_improvement_focus()

        event.input = AIModelNodeInput(
            prompt_variables={
                "improvement_focus": improvement_focus
            }
        )
        event.handled = True
    elif event.node_id == "improvement_implementer":
        # Get selected improvements from user
        all_improvements = get_improvements_from_result(
            execution_context.execution_results["improvement_flow.improvement_generator"]
        )
        selected_improvements = await select_improvements(all_improvements)

        event.input = FileOperationNodeInput(
            settings_override=FileOperationNodeSettings(
                base_directory=repo_dir,
                operations=selected_improvements,
                stage=True,
                commit=True,
                commit_message="Implemented selected code improvements"
            )
        )
        event.handled = True

# Register the input handler
event_bus.register(EventType.node_input_required, handle_input_required)

# Execute the agent
result = await code_review_agent.execute(
    execution_context=AgentExecutionContext(
        component_id="code_review_agent",
        component_definition=code_review_agent,
        run_context=run_context
    )
)
```

**Key Concepts:**

1. **Multi-Flow Agent**: The agent uses multiple flows for different stages of the process (analysis, improvement generation, implementation).
2. **Flow Dependencies**: Later flows depend on the results from earlier flows, accessed via hierarchical references.
3. **Interactive Selection**: The user can review and select which improvements to implement.
4. **Structured Outputs**: Each AI model node produces structured outputs that are consumed by subsequent nodes.

## Example 3: Collaborative Coding Agent

This example demonstrates an agent that facilitates collaborative coding by using specialized subagents for different aspects of development.

```python
from dhenara.agent.dsl import (
    AgentDefinition,
    AIModelNode,
    AIModelNodeSettings,
    EventType,
    FileOperationNode,
    FileOperationNodeSettings,
    FlowDefinition,
    FolderAnalyzerNode,
    FolderAnalyzerSettings,
)
from dhenara.ai.types import (
    AIModelCallConfig,
    ObjectTemplate,
    Prompt,
    ResourceConfigItem,
)

from src.agents.collab.types import DesignSpec, ImplementationPlan, TestPlan

# Create specialized subagents

# 1. Design agent - creates a detailed design specification
design_agent = AgentDefinition()
design_flow = FlowDefinition()

design_flow.node(
    "requirement_analyzer",
    AIModelNode(
        pre_events=[EventType.node_input_required],
        resources=ResourceConfigItem.with_models("claude-3-opus"),
        settings=AIModelNodeSettings(
            system_instructions=[
                "You are a software design expert. Create detailed design specifications from requirements."
            ],
            prompt=Prompt.with_dad_text(
                text=(
                    "Create a detailed design specification for the following requirements:\n\n"
                    "$var{requirements}\n\n"
                    "The design should include:\n"
                    "- Architecture overview\n"
                    "- Component breakdown\n"
                    "- API definitions\n"
                    "- Data models\n\n"
                    "Return a structured DesignSpec object."
                ),
            ),
            model_call_config=AIModelCallConfig(
                structured_output=DesignSpec,
                max_output_tokens=16000,
            ),
        ),
    ),
)

design_agent.flow("main", design_flow)

# 2. Implementation agent - implements the design
implementation_agent = AgentDefinition()
implementation_flow = FlowDefinition()

implementation_flow.node(
    "repo_analyzer",
    FolderAnalyzerNode(
        settings=FolderAnalyzerSettings(
            base_directory="$var{repo_dir}",
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
)

implementation_flow.node(
    "plan_creator",
    AIModelNode(
        resources=ResourceConfigItem.with_models("claude-3-7-sonnet"),
        settings=AIModelNodeSettings(
            system_instructions=[
                "You are an implementation planner. Create a detailed plan for implementing a design."
            ],
            prompt=Prompt.with_dad_text(
                text=(
                    "Create an implementation plan for the following design:\n\n"
                    "Design: $var{design_spec}\n\n"
                    "Repository structure: $hier{repo_analyzer}.outcome.structured\n\n"
                    "The plan should include:\n"
                    "- Files to create or modify\n"
                    "- Implementation order\n"
                    "- Key considerations\n\n"
                    "Return an ImplementationPlan object."
                ),
            ),
            model_call_config=AIModelCallConfig(
                structured_output=ImplementationPlan,
                max_output_tokens=16000,
            ),
        ),
    ),
)

implementation_flow.node(
    "code_implementer",
    FileOperationNode(
        settings=FileOperationNodeSettings(
            base_directory="$var{repo_dir}",
            operations_template=ObjectTemplate(
                expression="$hier{plan_creator}.outcome.structured.file_operations"
            ),
            stage=True,
            commit=True,
            commit_message="Implemented design according to plan"
        )
    )
)

implementation_agent.flow("main", implementation_flow)

# 3. Testing agent - creates and runs tests
testing_agent = AgentDefinition()
testing_flow = FlowDefinition()

testing_flow.node(
    "repo_analyzer",
    FolderAnalyzerNode(
        settings=FolderAnalyzerSettings(
            base_directory="$var{repo_dir}",
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
)

testing_flow.node(
    "test_planner",
    AIModelNode(
        resources=ResourceConfigItem.with_models("claude-3-7-sonnet"),
        settings=AIModelNodeSettings(
            system_instructions=[
                "You are a testing expert. Create comprehensive test plans for software components."
            ],
            prompt=Prompt.with_dad_text(
                text=(
                    "Create a test plan for the following implementation:\n\n"
                    "Design: $var{design_spec}\n\n"
                    "Implementation: $var{implementation_plan}\n\n"
                    "Repository structure: $hier{repo_analyzer}.outcome.structured\n\n"
                    "The test plan should include:\n"
                    "- Unit tests\n"
                    "- Integration tests\n"
                    "- Test file structure\n\n"
                    "Return a TestPlan object."
                ),
            ),
            model_call_config=AIModelCallConfig(
                structured_output=TestPlan,
                max_output_tokens=16000,
            ),
        ),
    ),
)

testing_flow.node(
    "test_implementer",
    FileOperationNode(
        settings=FileOperationNodeSettings(
            base_directory="$var{repo_dir}",
            operations_template=ObjectTemplate(
                expression="$hier{test_planner}.outcome.structured.file_operations"
            ),
            stage=True,
            commit=True,
            commit_message="Implemented tests based on test plan"
        )
    )
)

testing_agent.flow("main", testing_flow)

# Main collaborative agent
collaborative_agent = AgentDefinition()

# Add subagents
collaborative_agent.subagent("designer", design_agent)
collaborative_agent.subagent("implementer", implementation_agent)
collaborative_agent.subagent("tester", testing_agent)

# Coordination flow to manage the collaboration
coordination_flow = FlowDefinition()

coordination_flow.node(
    "coordinator",
    AIModelNode(
        pre_events=[EventType.node_input_required],
        resources=ResourceConfigItem.with_models("claude-3-5-haiku"),
        settings=AIModelNodeSettings(
            system_instructions=[
                "You are a project coordinator. Manage the collaboration between design, implementation, and testing teams."
            ],
            prompt=Prompt.with_dad_text(
                text=(
                    "Coordinate the development process for the following project:\n\n"
                    "Project: $var{project_name}\n\n"
                    "Requirements: $var{requirements}\n\n"
                    "Design: $hier{designer.main.requirement_analyzer}.outcome.structured\n\n"
                    "Implementation: $hier{implementer.main.plan_creator}.outcome.structured\n\n"
                    "Tests: $hier{tester.main.test_planner}.outcome.structured\n\n"
                    "Provide a summary of the development process and coordination efforts."
                ),
            ),
        ),
    ),
)

collaborative_agent.flow("coordination", coordination_flow)

# Execute the agent
result = await collaborative_agent.execute(
    execution_context=AgentExecutionContext(
        component_id="collaborative_agent",
        component_definition=collaborative_agent,
        run_context=run_context
    )
)
```

**Key Concepts:**

1. **Specialized Subagents**: Different aspects of development are handled by specialized subagents (design, implementation, testing).
2. **Agent Coordination**: The main agent coordinates the work of the subagents, ensuring proper information flow.
3. **Hierarchical References**: Results from subagents are referenced using the hierarchical reference system (`$hier{...}`).
4. **Progressive Refinement**: The process flows from high-level design to detailed implementation to comprehensive testing.

## Best Practices and Tips

### Dynamic Configuration

Make your agents more flexible by using variables for configuration:

```python
# Configuration through variables
repo_dir = "/path/to/repo"
models = ["claude-3-7-sonnet", "gpt-4.1-nano"]
temperature = 0.7

# Use variables in node definitions
ai_node = AIModelNode(
    resources=ResourceConfigItem.with_models(*models),
    settings=AIModelNodeSettings(
        model_call_config=AIModelCallConfig(
            options={"temperature": temperature}
        )
    )
)
```

### Error Handling

Implement comprehensive error handling to make your agents robust:

```python
# Add error handling to your flows
error_flow = FlowDefinition()

# Regular processing branch
normal_branch = FlowDefinition()
normal_branch.node("processor", processor_node)

# Error handling branch
error_branch = FlowDefinition()
error_branch.node("error_handler", error_handler_node)

# Add conditional to check for errors
main_flow.conditional(
    "error_check",
    statement=ObjectTemplate(expression="$hier{previous_node}.execution_status == 'FAILED'"),
    true_branch=error_branch,
    false_branch=normal_branch
)
```

### Incremental Development

Start simple and add complexity incrementally:

1. Build a basic flow with a single node
2. Test thoroughly
3. Add additional nodes and complexity
4. Refactor into reusable components
5. Build agents that coordinate multiple flows

### Testing Strategies

Develop effective testing strategies for your agents:

1. Unit test individual nodes with mock inputs
2. Create test flows to verify node interactions
3. Use simplified test environments
4. Log execution details for debugging
5. Implement observability to track agent behavior

## Conclusion

These examples demonstrate the flexibility and power of Dhenara Agent DSL (DAD) for building AI agents. By combining nodes, flows, and agents with the template and event systems, you can create sophisticated AI systems that solve complex problems.

Remember to follow best practices, leverage the hierarchical component model, and use the template engine effectively to create maintainable, reusable agent definitions.
