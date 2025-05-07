from abc import ABC

from dhenara.ai.types.shared.base import BaseEnum as DhenaraAIBaseEnum
from dhenara.ai.types.shared.base import BaseModel as DhenaraAIBaseModel


class BaseEnum(DhenaraAIBaseEnum):
    """Base class for all pydantic model definitions."""

    pass


class BaseModel(DhenaraAIBaseModel):
    """Base class for all pydantic model definitions."""

    @classmethod
    def from_json_file(cls, file_path: str):
        """
        Load a model instance from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            An instance of the model

        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
            ValidationError: If the JSON data doesn't match the model
        """

        import json
        from pathlib import Path

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(path) as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise json.JSONDecodeError(f"Invalid JSON in file {file_path}: {e!s}", e.doc, e.pos)
        except Exception as e:
            raise ValueError(f"Error while reading file: {file_path}: {e}")

        # This will raise ValidationError if data doesn't match the model
        return cls(**data)


class BaseModelABC(BaseModel, ABC):
    """Base class for all pydantic model abstact definitions."""

    pass
