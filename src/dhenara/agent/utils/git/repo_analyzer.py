import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class GitRepoAnalyzer:
    """Utility for analyzing repository structure and content"""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.ignored_patterns = self._parse_gitignore_files()

    def _parse_gitignore_files(self) -> list[str]:
        """
        Parse all .gitignore files in the repository

        Returns:
            List of patterns to ignore
        """
        ignore_patterns = []

        # Find all .gitignore files in the repo
        gitignore_files = list(self.repo_path.glob("**/.gitignore"))

        for gitignore_file in gitignore_files:
            try:
                with open(gitignore_file) as f:
                    parent_path = gitignore_file.parent
                    relative_parent = parent_path.relative_to(self.repo_path)

                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if not line or line.startswith("#"):
                            continue

                        # Handle negation patterns (inclusion)
                        if line.startswith("!"):
                            # We don't support ! patterns for simplicity
                            continue

                        # Handle directory-specific patterns
                        if str(relative_parent) != ".":
                            if not line.startswith("/"):
                                # Path is relative to .gitignore location
                                pattern = f"{relative_parent}/{line}"
                                ignore_patterns.append(pattern)
                            else:
                                # Path is anchored to .gitignore location
                                pattern = f"{relative_parent}{line}"
                                ignore_patterns.append(pattern)
                        else:
                            # Root .gitignore
                            ignore_patterns.append(line)
            except Exception as e:
                logger.warning(f"Error parsing .gitignore file {gitignore_file}: {e}")

        return ignore_patterns

    def _is_ignored(self, path: Path) -> bool:
        """
        Check if a path should be ignored based on .gitignore rules

        Args:
            path: Path to check

        Returns:
            True if the path should be ignored, False otherwise
        """
        # Always ignore .git directory
        if ".git" in path.parts:
            return True

        rel_path = path.relative_to(self.repo_path)
        rel_path_str = str(rel_path)

        for pattern in self.ignored_patterns:
            # Handle directory-only patterns (ending with /)
            if pattern.endswith("/") and path.is_dir():
                dir_pattern = pattern.rstrip("/")
                if self._match_gitignore_pattern(dir_pattern, rel_path_str):
                    return True
            # Handle file patterns or patterns without trailing slash
            elif self._match_gitignore_pattern(pattern, rel_path_str):
                return True

        return False

    def _match_gitignore_pattern(self, pattern: str, path: str) -> bool:
        """
        Match a gitignore pattern against a path

        Args:
            pattern: Gitignore pattern
            path: Path to check

        Returns:
            True if the pattern matches the path, False otherwise
        """
        # Remove leading slash for processing
        if pattern.startswith("/"):
            pattern = pattern[1:]
            # Anchored to repo root
            if not path.startswith(pattern):
                return False
            # Check if it's an exact match or the pattern matches a directory prefix
            return path == pattern or path.startswith(f"{pattern}/")

        # Handle directory wildcards
        if "**" in pattern:
            # Convert ** to regex
            regex_pattern = pattern.replace(".", "\\.").replace("**", ".*")
            return bool(re.match(f"^{regex_pattern}$", path))

        # Handle simple wildcards
        if "*" in pattern:
            parts = pattern.split("/")
            path_parts = path.split("/")

            if len(parts) > len(path_parts):
                return False

            for i, part in enumerate(parts):
                if i >= len(path_parts):
                    return False

                if "*" in part:
                    # Convert * to regex
                    regex_part = part.replace(".", "\\.").replace("*", "[^/]*")
                    if not re.match(f"^{regex_part}$", path_parts[i]):
                        return False
                elif part != path_parts[i]:
                    return False

            return True

        # Direct match or directory prefix
        return path == pattern or path.startswith(f"{pattern}/")

    def analyze_structure(self) -> dict:
        """
        Analyze the repository structure

        Returns:
            Dictionary with detailed repository structure information
        """
        if not self.repo_path.exists():
            return {"error": "Repository path does not exist"}

        try:
            # Get file structure
            file_structure = self._get_file_structure()

            # Detect programming languages
            languages = self._detect_languages()

            # Identify frameworks/libraries
            frameworks = self._identify_frameworks()

            # Get summary statistics
            stats = self._get_stats()

            return {
                "structure": file_structure,
                "languages": languages,
                "frameworks": frameworks,
                "stats": stats,
                "repo_path": str(self.repo_path),
            }
        except Exception as e:
            logger.error(f"Failed to analyze repository structure: {e}")
            return {"error": str(e)}

    def _get_file_structure(self) -> dict:
        """
        Analyze file and directory structure, respecting .gitignore

        Returns:
            Dictionary representing the file tree
        """
        structure = {"type": "directory", "name": self.repo_path.name, "children": []}
        self._build_tree(self.repo_path, structure)
        return structure

    def _build_tree(self, path: Path, node: dict) -> None:
        """
        Recursively build a tree structure from path, respecting .gitignore

        Args:
            path: Current path to analyze
            node: Current node in the tree to populate
        """
        if self._is_ignored(path):
            return

        # Process all items in the directory
        for item in path.iterdir():
            if self._is_ignored(item):
                continue

            if item.is_dir():
                child = {"type": "directory", "name": item.name, "children": []}
                node["children"].append(child)
                self._build_tree(item, child)
            else:
                node["children"].append(
                    {"type": "file", "name": item.name, "extension": item.suffix, "size": item.stat().st_size}
                )

    def _detect_languages(self) -> dict[str, int]:
        """
        Detect programming languages by file extension and count, respecting .gitignore

        Returns:
            Dictionary mapping language names to file counts
        """
        extension_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".h": "C/C++ Header",
            ".cs": "C#",
            ".go": "Go",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".rs": "Rust",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".md": "Markdown",
            ".json": "JSON",
            ".xml": "XML",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".sh": "Shell",
            ".bat": "Batch",
            ".ps1": "PowerShell",
        }

        language_counts = {}

        for file_path in self.repo_path.glob("**/*"):
            if file_path.is_file() and not self._is_ignored(file_path):
                ext = file_path.suffix.lower()
                if ext in extension_map:
                    lang = extension_map[ext]
                    language_counts[lang] = language_counts.get(lang, 0) + 1

        return language_counts

    def _identify_frameworks(self) -> list[str]:
        """
        Identify frameworks and libraries used in the repository, respecting .gitignore

        Returns:
            List of identified frameworks/libraries
        """
        frameworks = []

        # Check for package.json (Node.js)
        package_json_path = self.repo_path / "package.json"
        if package_json_path.exists() and not self._is_ignored(package_json_path):
            frameworks.append("Node.js")
            try:
                import json

                with open(package_json_path) as f:
                    package_data = json.load(f)

                # Add dependencies
                deps = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                for dep in deps:
                    if dep == "react":
                        frameworks.append("React")
                    elif dep == "angular":
                        frameworks.append("Angular")
                    elif dep == "vue":
                        frameworks.append("Vue.js")
                    # Add more framework detection as needed
            except:
                pass

        # Check for requirements.txt or setup.py (Python)
        req_path = self.repo_path / "requirements.txt"
        setup_path = self.repo_path / "setup.py"

        if (req_path.exists() and not self._is_ignored(req_path)) or (
            setup_path.exists() and not self._is_ignored(setup_path)
        ):
            frameworks.append("Python")

            # Check for specific Python frameworks (respecting .gitignore)
            flask_files = []
            django_files = []
            torch_files = []
            tensorflow_files = []

            for file_path in self.repo_path.glob("**/*.py"):
                if not self._is_ignored(file_path):
                    if file_path.name in ["flask.py", "Flask.py"]:
                        flask_files.append(file_path)
                    if "django" in str(file_path):
                        django_files.append(file_path)
                    if "torch" in str(file_path):
                        torch_files.append(file_path)
                    if "tensorflow" in str(file_path):
                        tensorflow_files.append(file_path)

            if flask_files:
                frameworks.append("Flask")
            if django_files:
                frameworks.append("Django")
            if torch_files:
                frameworks.append("PyTorch")
            if tensorflow_files:
                frameworks.append("TensorFlow")

        # Add more framework detection as needed
        return frameworks

    def _get_stats(self) -> dict:
        """
        Get summary statistics about the repository, respecting .gitignore

        Returns:
            Dictionary with statistics
        """
        total_files = 0
        total_directories = 0
        total_size = 0
        file_types = {}

        for item in self.repo_path.glob("**/*"):
            if self._is_ignored(item):
                continue

            if item.is_file():
                total_files += 1
                total_size += item.stat().st_size
                ext = item.suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
            elif item.is_dir():
                total_directories += 1

        return {
            "total_files": total_files,
            "total_directories": total_directories,
            "total_size_bytes": total_size,
            "file_types": file_types,
        }
