# git_handler.py
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FileIOBase:
    """
    File IO Base
    """

    def __init__(self, file_path: str | Path):
        """Initialize with repository path"""
        super().__init__(file_path=file_path)
        self.file_path = Path(file_path)

    def list_files(self, path: str | None = None, pattern: str | None = None) -> list[str]:
        """
        List files in the repository matching the given pattern

        Args:
            path: Optional path within the repository
            pattern: Optional glob pattern to match files

        Returns:
            List of file paths
        """
        search_path = self.file_path
        if path:
            search_path = search_path / path

        if pattern:
            return [str(p.relative_to(self.file_path)) for p in search_path.glob(pattern)]
        else:
            return [str(p.relative_to(self.file_path)) for p in search_path.glob("**/*") if p.is_file()]

    def create_file(self, file_path: str, content: str) -> bool:
        """
        Create a file with the given content

        Args:
            file_path: Path to the file, relative to the repository root
            content: Content to write to the file

        Returns:
            True if file was created successfully, False otherwise
        """
        try:
            full_path = self.file_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w") as f:
                f.write(content)

            return True
        except Exception as e:
            logger.error(f"Failed to create file {file_path}: {e}")
            return False

    def create_directory(self, dir_path: str) -> bool:
        """
        Create a directory in the repository

        Args:
            dir_path: Path to the directory, relative to the repository root

        Returns:
            True if directory was created successfully, False otherwise
        """
        try:
            full_path = self.file_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            return False
