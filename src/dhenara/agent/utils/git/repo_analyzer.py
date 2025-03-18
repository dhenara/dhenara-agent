import datetime
import logging
import re
import subprocess
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class GitRepoAnalyzerBase:
    """Utility for analyzing repository structure and content"""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.ignored_patterns = self._parse_gitignore_files()
        self.structure_context = None
        self.git_context = None
        self.submodules = {}
        self.subtrees = {}
        self.nested_git_repos = {}

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

    def analyze_basic_structure(self) -> dict:
        """
        Analyze the repository structure

        Returns:
            Dictionary with detailed repository structure information
        """
        if not self.repo_path.exists():
            return {"error": "Repository path does not exist"}

        try:
            # Detect submodules and subtrees first
            self._detect_submodules_and_subtrees()

            # Detect non-submodule git repositories
            self._detect_nested_git_repos()

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
                "submodules": self.submodules,
                "subtrees": self.subtrees,
                "nested_git_repos": self.nested_git_repos,
            }
        except Exception as e:
            logger.error(f"Failed to analyze repository structure: {e}")
            return {"error": str(e)}

    def _detect_submodules_and_subtrees(self) -> None:
        """
        Detect Git submodules and subtrees in the repository
        """
        # Check for submodules
        gitmodules_path = self.repo_path / ".gitmodules"
        if gitmodules_path.exists():
            try:
                # Parse .gitmodules file
                with open(gitmodules_path) as f:
                    content = f.read()

                # Extract submodule info using regex
                submodule_pattern = r'\[submodule\s+"([^"]+)"\]\s+path\s+=\s+([^\n]+)\s+url\s+=\s+([^\n]+)'
                matches = re.findall(submodule_pattern, content, re.MULTILINE)

                for name, path, url in matches:
                    path = path.strip()
                    url = url.strip()
                    submodule_path = self.repo_path / path
                    self.submodules[path] = {
                        "name": name,
                        "path": path,
                        "url": url,
                        "exists": submodule_path.exists(),
                    }
            except Exception as e:
                logger.warning(f"Error parsing .gitmodules file: {e}")

        # Try to detect subtrees using git command
        try:
            result = subprocess.run(
                ["git", "log", "--grep=git-subtree-dir:", "--pretty=format:%H %s"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                subtree_commits = result.stdout.strip().split("\n")

                for commit_line in subtree_commits:
                    if not commit_line.strip():
                        continue

                    parts = commit_line.split(" ", 1)
                    if len(parts) < 2:
                        continue

                    commit_hash, message = parts

                    # Extract subtree dir and prefix
                    dir_match = re.search(r"git-subtree-dir:\s*([^\s]+)", message)
                    prefix_match = re.search(r"git-subtree-split:\s*([^\s]+)", message)

                    if dir_match:
                        subtree_dir = dir_match.group(1)
                        subtree_hash = prefix_match.group(1) if prefix_match else None

                        # Check if directory exists
                        subtree_path = self.repo_path / subtree_dir
                        self.subtrees[subtree_dir] = {
                            "path": subtree_dir,
                            "commit": commit_hash,
                            "split_hash": subtree_hash,
                            "exists": subtree_path.exists(),
                        }
        except Exception as e:
            logger.warning(f"Error detecting subtrees: {e}")

    def _detect_nested_git_repos(self) -> None:
        """
        Detect Git repositories within the main repository that are not submodules
        """
        # Find all .git directories
        git_dirs = []
        for path in self.repo_path.glob("**/.git"):
            if path.is_dir() and not self._is_ignored(path.parent):
                rel_path = str(path.parent.relative_to(self.repo_path))
                git_dirs.append(rel_path)

        # Root git directory
        if (self.repo_path / ".git").exists():
            git_dirs = [d for d in git_dirs if d != "."]

        # Filter out known submodules
        submodule_paths = list(self.submodules.keys())
        nested_repos = [d for d in git_dirs if d not in submodule_paths]

        # Store information about nested repos
        for repo_path in nested_repos:
            full_path = self.repo_path / repo_path
            try:
                # Get remote URL if available
                remote_url = subprocess.run(
                    ["git", "config", "--get", "remote.origin.url"],
                    cwd=str(full_path),
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip()

                self.nested_git_repos[repo_path] = {
                    "path": repo_path,
                    "remote_url": remote_url,
                    "warning": "Nested Git repository that is not a registered submodule",
                }

                logger.warning(f"Found nested Git repository that is not a submodule: {repo_path}")
            except Exception as e:
                logger.warning(f"Error analyzing nested Git repository {repo_path}: {e}")

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

            rel_path = str(item.relative_to(self.repo_path))

            # Handle submodules and subtrees specially
            is_submodule = rel_path in self.submodules
            is_subtree = rel_path in self.subtrees
            is_nested_repo = rel_path in self.nested_git_repos

            if item.is_dir():
                child = {"type": "directory", "name": item.name, "children": []}

                # Add special markers
                if is_submodule:
                    child["is_submodule"] = True
                    child["submodule_info"] = self.submodules[rel_path]
                elif is_subtree:
                    child["is_subtree"] = True
                    child["subtree_info"] = self.subtrees[rel_path]
                elif is_nested_repo:
                    child["is_nested_repo"] = True
                    child["nested_repo_info"] = self.nested_git_repos[rel_path]

                node["children"].append(child)

                # Only recurse into the directory if it's not a special git dir
                if not (is_submodule or is_nested_repo):
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


class GitRepoAnalyzer(GitRepoAnalyzerBase):
    """Utility for analyzing repository structure and git metadata"""

    # [Existing methods remain unchanged]

    def analyze_repo_structure(self) -> dict:
        """
        Analyze repository structure including code relationships and dependencies

        Returns:
            Dictionary with detailed repository structure and code relationship information
        """
        if self.structure_context:
            return self.structure_context

        # Start with basic structure analysis
        basic_structure = self.analyze_basic_structure()

        # Add import and dependency analysis
        file_dependencies = self._analyze_code_dependencies()

        # Identify key components
        # key_components = self._identify_key_components()

        # Combine all structural information
        self.structure_context = {
            **basic_structure,
            "dependencies": file_dependencies,
            # "key_components": key_components, # TODO_FUTURE:
        }

        return self.structure_context

    def _analyze_code_dependencies(self) -> dict:
        """
        Analyze import statements and code dependencies across the repository

        Returns:
            Dictionary mapping files to their dependencies
        """
        dependencies = defaultdict(list)
        imports_by_file = defaultdict(list)

        # Focus on Python files for now (can be extended for other languages)
        for file_path in self.repo_path.glob("**/*.py"):
            # Skip submodules and nested repos
            rel_path_parts = file_path.relative_to(self.repo_path).parts

            # Skip analyzing files in submodules or nested repos
            in_special_repo = False
            for i in range(len(rel_path_parts)):
                check_path = str(Path(*rel_path_parts[: i + 1]))
                if check_path in self.submodules or check_path in self.subtrees or check_path in self.nested_git_repos:
                    in_special_repo = True
                    break

            if in_special_repo:
                continue

            if self._is_ignored(file_path):
                continue

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                # Simple regex to find import statements
                import_lines = re.findall(r"^(?:from|import)\s+([.\w]+)(?:\s+import\s+)?", content, re.MULTILINE)

                rel_path = str(file_path.relative_to(self.repo_path))
                imports_by_file[rel_path] = import_lines

                # Find files that might be related based on imports
                for imported in import_lines:
                    # Convert import to potential file path
                    parts = imported.split(".")

                    # Check if this is a local import
                    possible_module = self.repo_path / Path(*parts).with_suffix(".py")
                    possible_package = self.repo_path / Path(*parts) / "__init__.py"

                    if possible_module.exists() and not self._is_ignored(possible_module):
                        rel_module = str(possible_module.relative_to(self.repo_path))
                        dependencies[rel_path].append(rel_module)

                    elif possible_package.exists() and not self._is_ignored(possible_package):
                        rel_package = str(possible_package.relative_to(self.repo_path))
                        dependencies[rel_path].append(rel_package)

            except Exception as e:
                logger.warning(f"Error analyzing dependencies in {file_path}: {e}")

        return {"imports_by_file": dict(imports_by_file), "file_dependencies": dict(dependencies)}

    def _identify_key_components(self) -> dict:
        """
        Identify key components in the repository, respecting gitignore rules

        Returns:
            Dictionary with identified key components
        """
        key_components = {
            "entry_points": [],
            "config_files": [],
            "test_files": [],
            "documentation": [],
            "core_modules": [],
        }

        # Find potential entry points
        for file_path in self.repo_path.glob("**/*.py"):
            # Skip if in ignored paths, submodules, or nested repos
            rel_path_str = str(file_path.relative_to(self.repo_path))
            path_parts = rel_path_str.split("/")

            # Skip analyzing files in submodules or nested repos
            in_special_repo = False
            for i in range(len(path_parts)):
                check_path = "/".join(path_parts[: i + 1])
                if check_path in self.submodules or check_path in self.subtrees or check_path in self.nested_git_repos:
                    in_special_repo = True
                    break

            if in_special_repo or self._is_ignored(file_path):
                continue

            # Check if this might be an entry point
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    if "if __name__ == '__main__'" in content or 'if __name__ == "__main__"' in content:
                        key_components["entry_points"].append(rel_path_str)

                    # Check if this is a likely core module (imported by many files)
                    imported_count = 0
                    for deps in self._analyze_code_dependencies()["file_dependencies"].values():
                        if rel_path_str in deps:
                            imported_count += 1

                    if imported_count >= 3:  # Threshold for considering a file "core"
                        key_components["core_modules"].append(rel_path_str)
            except Exception as e:
                logger.warning(f"Error analyzing key component {file_path}: {e}")

        # Find documentation and config files
        for ext, category in [
            (".md", "documentation"),
            (".rst", "documentation"),
            (".txt", "documentation"),
            (".json", "config_files"),
            (".yaml", "config_files"),
            (".yml", "config_files"),
            (".ini", "config_files"),
            (".cfg", "config_files"),
            (".toml", "config_files"),
        ]:
            for file_path in self.repo_path.glob(f"**/*{ext}"):
                # Skip if in ignored paths, submodules, or nested repos
                rel_path_str = str(file_path.relative_to(self.repo_path))
                path_parts = rel_path_str.split("/")

                # Skip analyzing files in submodules or nested repos
                in_special_repo = False
                for i in range(len(path_parts)):
                    check_path = "/".join(path_parts[: i + 1])
                    if (
                        check_path in self.submodules
                        or check_path in self.subtrees
                        or check_path in self.nested_git_repos
                    ):
                        in_special_repo = True
                        break

                if in_special_repo or self._is_ignored(file_path):
                    continue

                key_components[category].append(rel_path_str)

        # Find test files
        for file_path in self.repo_path.glob("**/test_*.py"):
            if self._is_ignored(file_path):
                continue

            # Skip if in submodules or nested repos
            rel_path_str = str(file_path.relative_to(self.repo_path))
            path_parts = rel_path_str.split("/")

            in_special_repo = False
            for i in range(len(path_parts)):
                check_path = "/".join(path_parts[: i + 1])
                if check_path in self.submodules or check_path in self.subtrees or check_path in self.nested_git_repos:
                    in_special_repo = True
                    break

            if in_special_repo:
                continue

            key_components["test_files"].append(rel_path_str)

        for file_path in self.repo_path.glob("**/tests/**/*.py"):
            if self._is_ignored(file_path):
                continue

            # Skip if in submodules or nested repos
            rel_path_str = str(file_path.relative_to(self.repo_path))
            path_parts = rel_path_str.split("/")

            in_special_repo = False
            for i in range(len(path_parts)):
                check_path = "/".join(path_parts[: i + 1])
                if check_path in self.submodules or check_path in self.subtrees or check_path in self.nested_git_repos:
                    in_special_repo = True
                    break

            if in_special_repo:
                continue

            key_components["test_files"].append(rel_path_str)

        return key_components

    def analyze_git_metadata(self) -> dict:
        """
        Extract git metadata including commit history, authors, and file evolution

        Returns:
            Dictionary with git metadata information
        """
        if self.git_context:
            return self.git_context

        try:
            # Ensure we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0 or result.stdout.strip() != "true":
                logger.warning(f"Not a git repository: {self.repo_path}")
                return {"error": "Not a git repository"}

            # Get repository info
            repo_info = self._get_repo_info()

            # Get commit history
            commit_history = self._get_commit_history()

            # Get author statistics
            author_stats = self._get_author_stats()

            # Get file evolution data
            file_evolution = self._get_file_evolution()

            # Get commit message analysis
            commit_analysis = self._analyze_commit_messages()

            self.git_context = {
                "repo_info": repo_info,
                "commit_history": commit_history,
                "author_stats": author_stats,
                "file_evolution": file_evolution,
                "commit_analysis": commit_analysis,
            }

            return self.git_context

        except Exception as e:
            logger.error(f"Error analyzing git metadata: {e}")
            return {"error": str(e)}

    def _get_repo_info(self) -> dict:
        """Get basic repository information"""
        try:
            # Get remote URL
            remote_url = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()

            # Get current branch
            current_branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()

            # Get repository creation time (first commit)
            first_commit_time = (
                subprocess.run(
                    ["git", "log", "--reverse", "--format=%at", "--date=unix"],
                    cwd=str(self.repo_path),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                .stdout.strip()
                .split("\n")[0]
            )

            creation_date = (
                datetime.datetime.fromtimestamp(int(first_commit_time)).isoformat() if first_commit_time else None
            )

            return {"remote_url": remote_url, "current_branch": current_branch, "creation_date": creation_date}

        except Exception as e:
            logger.warning(f"Error getting repo info: {e}")
            return {}

    def _get_commit_history(self, max_commits: int = 100) -> list:
        """
        Get repository commit history

        Args:
            max_commits: Maximum number of commits to retrieve

        Returns:
            List of commit information dictionaries
        """
        try:
            # Get commit history with details
            result = subprocess.run(
                ["git", "log", f"-{max_commits}", "--pretty=format:%H|%an|%ae|%at|%s"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) < 5:
                    continue

                hash_val, author, email, timestamp, subject = parts

                # Convert Unix timestamp to ISO format
                date = datetime.datetime.fromtimestamp(int(timestamp)).isoformat()

                commits.append({"hash": hash_val, "author": author, "email": email, "date": date, "subject": subject})

            return commits

        except Exception as e:
            logger.warning(f"Error getting commit history: {e}")
            return []

    def _get_author_stats(self) -> dict:
        """Get statistics about repository authors"""
        try:
            # Get author commit counts
            result = subprocess.run(
                ["git", "shortlog", "-sne", "HEAD"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return {}

            authors = {}
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                # Parse the shortlog output format
                match = re.match(r"^\s*(\d+)\s+(.*?)\s+<(.+?)>$", line)
                if match:
                    count, name, email = match.groups()
                    authors[email] = {"name": name, "email": email, "commits": int(count)}

            return authors

        except Exception as e:
            logger.warning(f"Error getting author stats: {e}")
            return {}

    def _get_file_evolution(self, max_files: int = 20) -> dict:
        """
        Get file evolution information for the most significant files

        Args:
            max_files: Maximum number of files to analyze

        Returns:
            Dictionary with file evolution data
        """
        try:
            # Get the most changed files
            result = subprocess.run(
                ["git", "log", "--pretty=format:", "--name-only"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return {}

            # Count occurrences of each file
            file_counts = defaultdict(int)
            for filename in result.stdout.strip().split("\n"):
                if filename.strip():
                    file_counts[filename] += 1

            # Get the most frequently changed files
            top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:max_files]

            file_evolution = {}
            for filename, _ in top_files:
                # Skip files that are ignored or no longer exist
                file_path = self.repo_path / filename
                if self._is_ignored(file_path) or not file_path.exists():
                    continue

                # Get commit history for this file
                file_history = subprocess.run(
                    ["git", "log", "--pretty=format:%H|%an|%at|%s", "--follow", "--", filename],
                    cwd=str(self.repo_path),
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip()

                commits = []
                for line in file_history.split("\n"):
                    if not line:
                        continue

                    parts = line.split("|")
                    if len(parts) < 4:
                        continue

                    hash_val, author, timestamp, subject = parts
                    date = datetime.datetime.fromtimestamp(int(timestamp)).isoformat()

                    commits.append({"hash": hash_val, "author": author, "date": date, "subject": subject})

                file_evolution[filename] = {
                    "change_count": file_counts[filename],
                    "commits": commits[:10],  # Limit to 10 most recent commits
                }

            return file_evolution

        except Exception as e:
            logger.warning(f"Error getting file evolution: {e}")
            return {}

    def _analyze_commit_messages(self) -> dict:
        """
        Analyze commit messages to identify patterns and intents

        Returns:
            Dictionary with commit message analysis
        """
        try:
            # Get all commit messages
            result = subprocess.run(
                ["git", "log", "--pretty=format:%s"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return {}

            messages = result.stdout.strip().split("\n")

            # Simple analysis of commit messages
            keywords = {
                "feature": r"\b(feature|feat|add|implement|support)\b",
                "bugfix": r"\b(fix|bug|issue|problem|resolve|solve)\b",
                "refactor": r"\b(refactor|clean|improve|enhance|update)\b",
                "docs": r"\b(doc|comment|explain|clarify)\b",
                "test": r"\b(test|spec|assert|validate)\b",
                "chore": r"\b(chore|version|bump|release|merge)\b",
            }

            categories = defaultdict(list)
            category_counts = defaultdict(int)

            for msg in messages:
                if not msg:
                    continue

                for category, pattern in keywords.items():
                    if re.search(pattern, msg, re.IGNORECASE):
                        categories[category].append(msg)
                        category_counts[category] += 1

            # Calculate percentages
            total = len(messages)
            percentages = {cat: (count / total) * 100 if total > 0 else 0 for cat, count in category_counts.items()}

            return {
                "total_commits": total,
                "category_counts": dict(category_counts),
                "category_percentages": percentages,
                "sample_messages": {
                    cat: msgs[:5]  # Include up to 5 sample messages per category
                    for cat, msgs in categories.items()
                },
            }

        except Exception as e:
            logger.warning(f"Error analyzing commit messages: {e}")
            return {}

    def get_combined_context(self, query_context: str | None = None) -> dict:
        """
        Intelligently merge repository structure and git metadata based on query context

        Args:
            query_context: Optional query or context to help prioritize information

        Returns:
            Combined context optimized for the query
        """
        # Ensure we have analyzed both aspects
        if not self.structure_context:
            self.structure_context = self._analyze_repo_structure()

        if not self.git_context:
            self.git_context = self.analyze_git_metadata()

        # Start with a basic combined context
        combined = {
            "repo_path": str(self.repo_path),
            "languages": self.structure_context.get("languages", {}),
            "frameworks": self.structure_context.get("frameworks", []),
            "repo_stats": self.structure_context.get("stats", {}),
        }

        # Add git repository information
        combined["repo_info"] = self.git_context.get("repo_info", {})

        # If we have a query context, use it to prioritize information
        if query_context:
            # Extract potential file mentions from the query
            mentioned_files = self._extract_file_mentions(query_context)

            # Determine if query is more about structure or history
            is_structure_focused = self._is_structure_query(query_context)
            is_history_focused = self._is_history_query(query_context)
            is_author_focused = self._is_author_query(query_context)

            # Prioritize based on query focus
            if is_structure_focused:
                combined["file_structure"] = self.structure_context.get("structure", {})
                combined["key_components"] = self.structure_context.get("key_components", {})
                combined["dependencies"] = self.structure_context.get("dependencies", {})

                # Add minimal git info
                combined["commit_analysis"] = self.git_context.get("commit_analysis", {})

            elif is_history_focused:
                combined["commit_history"] = self.git_context.get("commit_history", [])
                combined["commit_analysis"] = self.git_context.get("commit_analysis", {})
                combined["file_evolution"] = self.git_context.get("file_evolution", {})

                # Add minimal structure info
                combined["key_components"] = self.structure_context.get("key_components", {})

            elif is_author_focused:
                combined["author_stats"] = self.git_context.get("author_stats", {})
                combined["commit_history"] = self.git_context.get("commit_history", [])

                # Add minimal structure info
                combined["key_components"] = self.structure_context.get("key_components", {})

            else:
                # Balanced approach for general queries
                combined["key_components"] = self.structure_context.get("key_components", {})
                combined["commit_analysis"] = self.git_context.get("commit_analysis", {})
                combined["file_evolution"] = {
                    k: v
                    for k, v in self.git_context.get("file_evolution", {}).items()
                    if k in self.structure_context.get("key_components", {}).get("core_modules", [])
                }

            # Add specific information about mentioned files
            if mentioned_files:
                file_info = {}
                for file in mentioned_files:
                    # Get structural info
                    file_dependencies = (
                        self.structure_context.get("dependencies", {}).get("file_dependencies", {}).get(file, [])
                    )
                    file_imports = (
                        self.structure_context.get("dependencies", {}).get("imports_by_file", {}).get(file, [])
                    )

                    # Get git info
                    file_evolution = self.git_context.get("file_evolution", {}).get(file, {})

                    file_info[file] = {
                        "dependencies": file_dependencies,
                        "imports": file_imports,
                        "evolution": file_evolution,
                    }

                combined["mentioned_files"] = file_info
        else:
            # No query context, provide a balanced view
            combined["key_components"] = self.structure_context.get("key_components", {})
            combined["commit_analysis"] = self.git_context.get("commit_analysis", {})

            # Include top 5 core modules with their evolution
            core_modules = self.structure_context.get("key_components", {}).get("core_modules", [])[:5]
            combined["core_modules_evolution"] = {
                module: self.git_context.get("file_evolution", {}).get(module, {}) for module in core_modules
            }

        return combined

    # TODO_FUTURE: Below are not tested
    # May be we should user an LLM call for this to be more inteligent
    def _extract_file_mentions(self, query: str) -> list[str]:
        """Extract potential file mentions from a query string"""
        # Look for patterns like file.py, dir/file.py, or "file.py"
        file_patterns = [
            r"\b[\w\-\.\/]+\.py\b",
            r"\b[\w\-\.\/]+\.js\b",
            r"\b[\w\-\.\/]+\.java\b",
            r"\b[\w\-\.\/]+\.ts\b",
            r"\b[\w\-\.\/]+\.html\b",
            r"\b[\w\-\.\/]+\.css\b",
            r"\b[\w\-\.\/]+\.md\b",
            r"\b[\w\-\.\/]+\.json\b",
            r"\b[\w\-\.\/]+\.yaml\b",
            r"\b[\w\-\.\/]+\.yml\b",
            r'"([\w\-\.\/]+\.\w+)"',
            r"'([\w\-\.\/]+\.\w+)'",
        ]

        mentioned_files = []
        for pattern in file_patterns:
            matches = re.findall(pattern, query)
            mentioned_files.extend(matches)

        # Remove duplicates
        return list(set(mentioned_files))

    def _is_structure_query(self, query: str) -> bool:
        """Check if a query is focused on repository structure"""
        structure_keywords = [
            "structure",
            "organization",
            "layout",
            "files",
            "directories",
            "modules",
            "components",
            "architecture",
            "design",
            "organize",
            "dependency",
            "import",
            "relation",
            "structure",
            "code",
        ]

        for keyword in structure_keywords:
            if keyword in query.lower():
                return True

        return False

    def _is_history_query(self, query: str) -> bool:
        """Check if a query is focused on repository history"""
        history_keywords = [
            "history",
            "commit",
            "change",
            "evolution",
            "timeline",
            "modify",
            "update",
            "version",
            "when",
            "time",
            "date",
            "development",
            "progress",
            "changelog",
            "log",
        ]

        for keyword in history_keywords:
            if keyword in query.lower():
                return True

        return False

    def _is_author_query(self, query: str) -> bool:
        """Check if a query is focused on authors/contributors"""
        author_keywords = [
            "author",
            "contributor",
            "who",
            "wrote",
            "developer",
            "maintainer",
            "owner",
            "responsible",
            "contribution",
        ]

        for keyword in author_keywords:
            if keyword in query.lower():
                return True

        return False
