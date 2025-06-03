from typing import Any, Literal

from pydantic import Field, model_validator

from dhenara.agent.types.base import BaseModel

from .file_operation import FileMetadata


class FileInfo(BaseModel):
    """Information about a file."""

    path: str = Field(..., description="Path to the file with name and extension")

    content_preview: str | None = Field(default=None, description="Preview of the file content")
    content: str | None = Field(default=None, description="Full content of the file")
    truncated: bool | None = Field(default=None, description="Whether the content was forced to truncate")
    # Currently content_structure read is only supported for python files
    content_structure: str | None = Field(default=None, description="Structure of the content (e.g., for Python files)")

    metadata: FileMetadata | None = Field(default=None, description="File Metadata")

    error: str | None = Field(default=None, description="Error message, if any")
    word_count: int | None = Field(default=None, description="Word count of the file")
    is_text: bool | None = Field(default=None, description="Whether the file is a text file")
    mime_type: str | None = Field(default=None, description="MIME type of the file")
    summary: str | None = Field(default=None, description="Summary of the file content")


class DirectoryInfo(BaseModel):
    """Information about a directory."""

    path: str = Field(..., description="Path to the directory with name")
    children: list[Any] = Field(default_factory=list, description="List of children. Can be FileInfo or DirectoryInfo")
    file_count: int | None = Field(default=None, description="Number of files in the directory")
    dir_count: int | None = Field(default=None, description="Number of subdirectories in the directory")
    truncated: bool | None = Field(default=None, description="Whether the directory listing was truncated")
    # Dir metadata fields
    size: int | None = Field(default=None, description="Size of the directory in bytes")
    created: str | None = Field(default=None, description="Creation timestamp")
    modified: str | None = Field(default=None, description="Last modification timestamp")
    accessed: str | None = Field(default=None, description="Last accessed timestamp")
    permissions: str | None = Field(default=None, description="File permissions in octal format")

    errors: list[str] | None = Field(
        default=None, description="Error messages of failed reads ( could be multiple for a dir"
    )
    word_count: int | None = Field(default=None, description="Total words in the file/dir")
    file_types: dict[str, int] | None = Field(default=None, description="Type of files and their count in dir")
    total_files: int | None = Field(default=None, description="Total files analyzed")
    total_directories: int | None = Field(default=None, description="Total directories analyzed")
    total_size: int | None = Field(default=None, description="Total size of analyzed items")
    gitignore_patterns: list[str] | None = Field(default=None, description="gitignore patterns in dir")


# INFO:
# Splitting  FolderAnalysisOperation into 2, send simple schema for LLM strucutred output
class FileSystemAnalysisOperation(BaseModel):
    """
    Defines a file system analysis operation to examine files and directories in a repository.
    This is used to gather context about code repositories, documentation, or any file system
    to help answer user questions about their project.
    """

    # Operation type
    operation_type: Literal[
        "analyze_folder",
        "analyze_file",
        "find_files",
        "get_structure",
        "get_tree_diagram",
    ] = Field(
        ...,
        description=(
            "The type of analysis to perform:\n"
            "- 'analyze_folder': Recursively examine a directory, retrieving all files info and contents (optional)\n"
            "- 'analyze_file': Analyze a single file, retrieving its content or structure\n"
            "- 'find_files': Search for files in a directory that match certain patterns\n"
            "- 'get_structure': Get only the directory structure without file contents for a quick overview"
            "- 'get_tree_diagram': Get Tree Diagram of the directory structure\n"
        ),
    )
    # Path specification - now supports both single path and multiple paths
    path: str | list[str] = Field(
        ...,
        description=(
            "Path(s) to the folder(s) or file(s) to analyze. Can be a single path string or a list of paths. "
            "Each path can be relative to the base directory or absolute. "
            "Examples: 'src', ['src', 'tests'], 'src/main.py', ['src/main.py', 'README.md'], './docs', ['/absolute/path/to/file.txt']. "  # noqa: E501
            "Use this to specify exactly which part(s) of the repository you want to examine. "
            "When multiple paths are provided, they will all be processed with the same operation settings. "
            "Usually this will be relative path(s) for sending content to LLM."
        ),
    )
    # Content reading options
    content_read_mode: Literal["none", "preview", "full", "structure"] = Field(
        ...,
        description=(
            "How to process and represent file content:\n"
            "- 'none': The actual content of files will NOT be read or included in the analysis results. "
            "Use when you only need to understand file structure/organization.\n"
            "- 'preview': Include a short preview of file contents (first few lines). "
            "Useful for getting a glimpse of what files contain without reading everything.\n"
            "- 'full': Return the raw text content of the file. "
            "Use when you need to examine the code or text inside files to answer questions.\n"
            "- 'structure': For supported file types like Python, extract structural elements like classes, "
            "functions, and imports instead of raw text. Useful for understanding code organization without "
            "reading all implementation details.\n"
            "This significantly affects the amount of text returned, so choose the appropriate mode for your needs."
        ),
    )

    additional_gitignore_paths: list[str] | None = Field(
        default=None,
        description=(
            "Additional paths to .gitignore files that should be considered when analyzing files. "
            "These paths can be relative to the base directory or absolute. "
            "By default, the system automatically processes the .gitignore file in the specified "
            "path (if it exists) as well as any .gitignore files in parent directories. "
            "Use this parameter while setting the `path` to a sub dir of the a git repo."
            "Example: ['configs/.custom-ignore', '/path/to/another/.gitignore']"
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def validate_content_read_mode(cls, values):
        if values.get("operation_type") in ["find_files", "get_structure", "get_tree_diagram"]:
            values["content_read_mode"] = "none"
        return values


class FolderAnalysisOperation(FileSystemAnalysisOperation):
    """
    Defailed FileSystem Analysis operation with fine grained control.
    FileSystemAnalysisOperation is intentionally kept simple for sending schema to LLMs
    """

    include_root_in_path: bool = Field(
        default=False,
        description=(
            "Whether to include the root directory name in reported paths. If True, all paths will be prefixed with "
            "the root directory name, which helps maintain context about where files are located. "
            "Example: With root dir 'my_project', paths will be 'my_project/src/file.py' instead of 'src/file.py'."
            "Usually this will be false for sending content to LLM."
        ),
    )

    # Traversal and filtering options
    max_depth: int | None = Field(
        default=None,
        description=(
            "Maximum directory depth to traverse when analyzing folders. Use this to limit analysis to "
            "top-level directories only or include deeper subdirectories. If None, all nested directories "
            "will be included. Example: 0 means only the specified directory, 1 includes its immediate children, etc."
        ),
        ge=0,
    )

    respect_gitignore: bool = Field(
        default=True,
        description=(
            "Whether to automatically exclude files listed in .gitignore from analysis. "
            "Set to True (default) to ignore files that are likely not relevant to the codebase. "
            "Set to False if you specifically need to examine files that are normally ignored by git."
        ),
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description=(
            "Patterns of files/directories to exclude from analysis (using glob format). "
            "Use this to ignore irrelevant files like cache directories, build artifacts, or large data files. "
            "Examples: ['*.pyc', '__pycache__', 'node_modules', '*.log', 'build/*']. "
            "Patterns with '/' are path-relative, otherwise they match against filenames only."
            "Usually this will empty for a git repo with a gitignore, but make sure `respect_gitignore` is set True."
        ),
    )
    include_hidden: bool = Field(
        default=False,
        description=(
            "Whether to include hidden files and directories (those starting with '.') in the analysis. "
            "Set to True if you need to examine configuration files like '.gitignore' or '.env', "
            "otherwise these are skipped by default."
        ),
    )

    # Content reading options

    content_exclusions: list[Literal["doc_strings", "comments", "blank_lines"]] = Field(
        default_factory=list,
        description=(
            "Elements to exclude when reading file content in 'full' mode. Options include:\n"
            "- 'doc_strings': Remove docstrings (triple-quoted strings) from the content\n"
            "- 'comments': Remove single-line and inline comments\n"
            "- 'blank_lines': Remove empty lines from the content\n"
            "This helps reduce token usage while retaining the core code logic. Only applies when "
            "content_read_mode is 'full'."
        ),
    )

    content_structure_detail_level: Literal["basic", "standard", "detailed", "full"] = Field(
        default="detailed",
        description=(
            "When content_read_mode is 'structure', controls how much detail to include:\n"
            "- 'basic': Just names of classes, functions, and imports\n"
            "- 'standard': Adds signatures, docstrings, and inheritance information\n"
            "- 'detailed': Adds type hints, decorators, and nested definitions\n"
            "- 'full': Includes simplified function bodies and additional context\n"
            "This is primarily useful for Python files to focus on API structure rather than implementation details."
        ),
    )

    @property
    def read_content(self):
        return self.content_read_mode != "none"

    @property
    def include_content_preview(self):
        return self.content_read_mode == "preview"

    # Size and content limits
    max_file_size: int | None = Field(
        default=1024 * 1024,  # 1MB default
        description=(
            "Maximum file size in bytes to consider for content analysis. Files larger than this will have "
            "their metadata included but content skipped. Default is 1MB. Set to None for no limit, but be "
            "cautious with very large files. This prevents accidentally trying to process large binary files or "
            "data files that would overwhelm the context window."
        ),
    )

    max_words_per_file: int | None = Field(
        default=None,
        description=(
            "Maximum number of words to include from each file when reading content. If a file exceeds this limit, "
            "it will be truncated. Use this to prevent single large files from dominating the context. "
            "Example: 500 would include only the first 500 words of each file. Set to None for no per-file limit."
        ),
        ge=0,
    )

    max_total_words: int | None = Field(
        default=None,
        description=(
            "Maximum total number of words to include across all files analyzed. Once this limit is reached, "
            "remaining files will have their content skipped. This helps control the total amount of text "
            "returned when analyzing large repositories. Set to None for no overall word limit, but be mindful "
            "of context window limitations."
        ),
        ge=0,
    )

    # Analysis and display options
    include_primary_meta: bool = Field(
        default=False,
        description=(
            "Whether to include primary metadata of file/directory statistics and metadata ( total_files, "
            "total_directories, total_size, mime_type, is_text, truncated, etc.). Enable this when you need to analyze "
            "file properties beyond content, such as identifying recently modified files or understanding "
            "file sizes. Typically set to False when sending results to LLMs to save context space."
        ),
    )
    include_stats_and_meta: bool = Field(
        default=False,
        description=(
            "Whether to include detailed file/directory statistics and metadata (size, creation date, "
            "modification date, access times, permissions, etc.). Enable this when you need to analyze "
            "file properties beyond content, such as identifying recently modified files or understanding "
            "file sizes. Typically set to False when sending results to LLMs to save context space."
        ),
    )

    generate_tree_diagram: bool = Field(
        default=False,
        description=(
            "Whether to generate an ASCII tree diagram of the directory structure for easy visualization. "
            "Example: root/\n  ├── src/\n  │   ├── main.py\n  │   └── utils.py\n  └── tests/\n"
            "This provides a clear visual representation of the project organization."
        ),
    )

    tree_diagram_max_depth: int | None = Field(
        default=None,
        description=(
            "Maximum depth to include in the tree diagram. Use this to limit the tree diagram to only "
            "show top-level directories and files when you don't need the complete tree. "
            "Only applies when generate_tree_diagram is True. If None, uses max_depth or shows the full tree."
        ),
    )

    tree_diagram_include_files: bool = Field(
        default=True,
        description=(
            "Whether to include files in the tree diagram or only show directories. "
            "Set to False for a cleaner diagram that only shows directory structure in large repositories. "
            "Only applies when generate_tree_diagram is True."
        ),
    )

    def validate_content_type(self) -> bool:
        """Validates that the parameters are valid for this operation type"""
        # if self.operation_type in ["analyze_folder", "analyze_file", "find_files", "get_structure"] and not self.path:
        #    return False
        return True
