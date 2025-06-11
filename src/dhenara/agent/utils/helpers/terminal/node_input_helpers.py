# ruff: noqa: FBT003
import asyncio
import json

from dhenara.agent.dsl import (
    AIModelNodeInput,
    AIModelNodeSettings,
    FileOperationNodeInput,
    FileOperationNodeSettings,
    FolderAnalyzerNodeInput,
    FolderAnalyzerSettings,
)
from dhenara.agent.dsl.inbuilt.flow_nodes.defs.types import (
    FileOperation,
    FolderAnalysisOperation,
)
from dhenara.agent.types.base._base_type import BaseModel
from dhenara.ai.types import AIModelCallConfig, ResourceConfigItem


async def async_input(prompt: str) -> str:
    """Asynchronous version of input function"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))


async def get_yes_no_input(prompt: str, default: bool = True) -> bool:
    """Helper function to get yes/no input with default option"""
    default_str = "Y/n" if default else "y/N"
    response = await async_input(f"{prompt} [{default_str}]: ")
    if not response:
        return default
    return response.lower() in ("y", "yes")


async def get_menu_choice(options: list[str], prompt: str = "Choose an option:") -> int:
    """Display a menu and get user choice"""
    print(prompt)
    for idx, option in enumerate(options, 1):
        print(f"{idx}. {option}")

    while True:
        choice = await async_input("Enter number: ")
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                return choice_num - 1
            print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")


async def get_folder_analyzer_operation_input(
    base_directory: str,
    predefined_exclusion_patterns: list[list[str]],
) -> FolderAnalysisOperation:
    """Collect user input for a single folder analysis operation"""
    # Operation type selection
    operation_types = [
        "analyze_folder - Recursively examine a directory",
        "analyze_file - Analyze a single file",
        "find_files - Search for files matching patterns",
        "get_structure - Get directory structure without contents",
    ]
    operation_type_idx = await get_menu_choice(operation_types, "Select operation type:")
    operation_type = operation_types[operation_type_idx].split(" - ")[0]

    # Get path
    path = await async_input(f"Enter path (relative to base dir `{base_directory}`): ")

    # Get essential parameters based on operation type
    # include_root = await get_yes_no_input("Include root directory in path?", False)
    include_root = False
    respect_gitignore = await get_yes_no_input("Respect .gitignore files?", True)
    include_hidden = await get_yes_no_input("Include hidden files (starting with .)?", False)

    # Content reading options
    read_content = await get_yes_no_input("Read file contents?", True)

    content_read_mode = "full"
    content_detail_level = "basic"

    if read_content:
        content_modes = [
            "full - Return the raw text content",
            "structure - Extract structural elements",
        ]
        content_mode_idx = await get_menu_choice(content_modes, "Select content read mode:")
        content_read_mode = content_modes[content_mode_idx].split(" - ")[0]

        if content_read_mode == "structure":
            detail_levels = ["basic", "standard", "detailed", "full"]
            detail_idx = await get_menu_choice(detail_levels, "Select structure detail level:")
            content_detail_level = detail_levels[detail_idx]
    else:
        content_read_mode = "none"

    _patterns = [*predefined_exclusion_patterns, "No exclussion patters"]
    ep_idx = await get_menu_choice(_patterns, "Select a predefined exclusion_pattern:")
    if ep_idx == len(_patterns) - 1:  # Check if the last option is selected
        default_exclusion_patterns = []
    else:
        default_exclusion_patterns = predefined_exclusion_patterns[ep_idx]

    try:
        # Create operation with collected parameters
        operation = FolderAnalysisOperation(
            operation_type=operation_type,
            path=path,
            include_root_in_path=include_root,
            respect_gitignore=respect_gitignore,
            include_hidden=include_hidden,
            content_read_mode=content_read_mode,
            content_structure_detail_level=content_detail_level,
            exclude_patterns=default_exclusion_patterns,
            # content_exclusions=[],
        )
    except Exception as e:
        raise e

    # Advanced options (optional)
    if await get_yes_no_input("Configure advanced options?", False):
        # Depth options
        max_depth_str = await async_input("Maximum directory depth (leave empty for unlimited): ")
        if max_depth_str:
            operation.max_depth = int(max_depth_str)

        # Exclusion patterns
        print("\nDefault exclusion patterns set:")
        for pattern in default_exclusion_patterns:
            print(f"  - {pattern}")
        print()

        add_default_exclusion_patterns = await get_yes_no_input("Add above default exclude patterns? ", True)
        exclusion_patterns = default_exclusion_patterns if add_default_exclusion_patterns else []

        while await get_yes_no_input("Add additional exclusion pattern?", False):
            pattern = await async_input("Enter pattern (e.g. '*.pyc', 'node_modules'): ")
            exclusion_patterns.append(pattern)

        operation.exclude_patterns = exclusion_patterns

        # Size limits
        max_file_size_str = await async_input("Maximum file size in KB (default: 1024): ")
        if max_file_size_str:
            operation.max_file_size = int(max_file_size_str) * 1024

        # Visualization options
        generate_tree = await get_yes_no_input("Generate tree diagram?", False)
        operation.generate_tree_diagram = generate_tree

        if generate_tree:
            operation.tree_diagram_include_files = await get_yes_no_input("Include files in tree diagram?", True)

    return operation


async def get_variable_dict(variable_name: str, folder_path: str | None = None) -> dict:
    read_var_from_file = await get_yes_no_input(f"Read {variable_name} from a file?", True)
    if read_var_from_file:
        import os

        variable_value = None
        valid_dir = False
        resolved_path = None

        # If a folder path is provided, try to resolve it
        if folder_path:
            # Try paths in different ways to find the directory
            possible_paths = [
                folder_path,  # As provided
                os.path.join(os.getcwd(), folder_path),  # Relative to CWD
                os.path.abspath(folder_path),  # Absolute path
            ]

            for path in possible_paths:
                if os.path.isdir(path):
                    valid_dir = True
                    resolved_path = path
                    print(f"Found directory at: {resolved_path}")
                    break

            if valid_dir:
                print(f"\nFiles in {resolved_path}:")
                files = []

                # Collect files from the specified directory
                try:
                    for item in os.listdir(resolved_path):
                        item_path = os.path.join(resolved_path, item)
                        if os.path.isfile(item_path):
                            files.append(item)

                    # Display the files
                    if files:
                        # for i, file in enumerate(files):
                        #    print(f"{i+1}. {file}")

                        # Add option for manual path entry
                        files.append("Enter custom file path...")

                        # Display files for selection
                        file_idx = await get_menu_choice(files, "Select a file:")
                        selected_option = files[file_idx]

                        if selected_option == "Enter custom file path...":
                            use_custom_path = True
                        else:
                            file_path = os.path.join(resolved_path, selected_option)
                            use_custom_path = False
                    else:
                        print("No files found in the directory.")
                        use_custom_path = True
                except Exception as e:
                    print(f"Error accessing directory: {e}")
                    use_custom_path = True
            else:
                print(f"Directory '{folder_path}' not found. Tried: {', '.join(possible_paths)}")
                use_custom_path = True
        else:
            use_custom_path = True

        # Handle custom path entry if needed
        while variable_value is None:
            if use_custom_path:
                file_path = await async_input("Enter the path to the file: ")

                # Try to resolve file path in different ways
                if not os.path.isfile(file_path):
                    possible_file_paths = [
                        file_path,
                        os.path.join(os.getcwd(), file_path),
                        os.path.abspath(file_path),
                    ]

                    for path in possible_file_paths:
                        if os.path.isfile(path):
                            file_path = path
                            print(f"Found file at: {file_path}")
                            break

            try:
                with open(file_path) as file:  # noqa: ASYNC230
                    variable_value = file.read()
                print(f"Successfully read content from {file_path}")
            except Exception as e:
                variable_value = None
                print(f"Error reading file: {e}")
                print("Please enter a valid file path.")
                use_custom_path = True  # Force custom path on error
    else:
        variable_value = await async_input(f"Enter your {variable_name}: ")

    return {variable_name: variable_value}


async def get_ai_model_node_input(
    node_def_settings: AIModelNodeSettings,
    models: list[str] | None = None,
    models_with_options: dict[str, dict] | None = None,
    enable_option_update: bool = True,
    structured_output: BaseModel | None = None,
):
    print("\n=== AI Model Selection ===\n")

    if models_with_options is None:
        models_with_options = {}

    available_models = models if models is not None else list(models_with_options.keys())
    available_models = (
        available_models if available_models else ResourceConfigItem.get_model_names(node_def_settings.resources)
    )

    if len(available_models) == 1:
        selected_model = available_models[0]
    else:
        selected_model_idx = await get_menu_choice(available_models, "Select an AI model:")
        selected_model = available_models[selected_model_idx]

    print(f"Using model: {selected_model}")

    node_input = AIModelNodeInput()

    # Update options if available and enabled
    if models_with_options and selected_model not in models_with_options.keys():
        raise ValueError(f"Selected model {selected_model} is not in models_with_options")

    update_options = enable_option_update and selected_model in models_with_options.keys()
    # Update structured output if provided
    update_structured = structured_output is not None
    update_model_call_config = update_options or update_structured
    update_settings = node_def_settings is not None

    if update_settings:
        try:
            # Do not user model_copy, as the models->resources are taken care only while the obj is constructed
            _settings_dict = node_def_settings.model_dump()
            _settings_dict.update(
                {
                    "models": [selected_model],
                    "resources": None,
                }
            )
            _settings = AIModelNodeSettings(**_settings_dict)

            # Only modify model_call_config if needed
            if update_model_call_config:
                # Get base parameters from existing config
                _params = _settings.model_call_config.model_dump()

                if update_options:
                    _params["options"] = models_with_options[selected_model]
                    print(f"Updated model options for {selected_model}")

                if update_structured:
                    _params["structured_output"] = structured_output
                    print(f"Updated structured output to {structured_output}")

                try:
                    # Create new config with updated parameters
                    _settings.model_call_config = AIModelCallConfig(**_params)
                except Exception as e:
                    raise ValueError(f"AI Model Event handler: Error: {e}")

            node_input.settings_override = _settings
        except Exception as e:
            print(f"ERROR while getting node input: {e}")
            raise e

    return node_input


async def get_folder_analyzer_node_input(
    node_def_settings: AIModelNodeSettings,
    base_directory: str,
    predefined_exclusion_patterns: list[list[str]],
):
    print("\n=== Repository Analysis Configuration ===\n")
    operations = []

    # Allow users to add multiple operations
    while True:
        operation = await get_folder_analyzer_operation_input(
            base_directory=base_directory,
            predefined_exclusion_patterns=predefined_exclusion_patterns,
        )

        operations.append(operation)

        if not await get_yes_no_input("Add another analysis operation?", False):
            break

    # Display summary of configured operations
    print("\nConfigured operations:")
    for i, op in enumerate(operations, 1):
        print(f"{i}. {op.operation_type} - {op.path}")

    # Create the node input with the operations
    node_input = FolderAnalyzerNodeInput(
        settings_override=FolderAnalyzerSettings(
            base_directory=base_directory,
            operations=operations,
        )
    )
    return node_input


async def get_file_operations_node_input(
    node_def_settings: AIModelNodeSettings,
    base_directory: str,
    file_operations_json_path: str,
):
    def _read_file():
        with open(file_operations_json_path) as file:
            ops_dict_list = json.load(file)
            ops = [FileOperation(**ops_dict_item) for ops_dict_item in ops_dict_list]
            return ops

    operations = _read_file()
    node_input = FileOperationNodeInput(
        settings_override=FileOperationNodeSettings(
            base_directory=base_directory,
            operations=operations,
            stage=True,
            commit=False,  # Commit handled in the coordinator
            commit_message="$var{run_id}: Implemented plan step",
        ),
    )

    return node_input
