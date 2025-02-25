from typing import Union

from dhenara.agent.types.flow import ConversationFieldEnum, ConversationNodeFieldEnum, ConversationSpaceFieldEnum, StorageEntityTypeEnum
from dhenara.ai.types.shared.base import BaseModel
from pydantic import Field, field_validator

FieldType = Union[ConversationFieldEnum, ConversationNodeFieldEnum, ConversationSpaceFieldEnum]


class StorageSettings(BaseModel):
    """
    Settings for database storage actions (save/delete) on conversation entities.

    Specifies which fields should be saved or deleted for different storage entity types.

    Attributes:
        save: Mapping of storage entity types to lists of fields that should be saved
        delete: Mapping of storage entity types to lists of fields that should be deleted
    """

    save: dict[StorageEntityTypeEnum, list[FieldType]] = Field(
        default_factory=dict,
        description="Mapping of entity types to fields that should be saved",
        example={
            StorageEntityTypeEnum.conversation: [ConversationFieldEnum.title],
            StorageEntityTypeEnum.conversation_node: [ConversationNodeFieldEnum.inputs, ConversationNodeFieldEnum.outputs],
        },
    )

    delete: dict[StorageEntityTypeEnum, list[FieldType]] = Field(
        default_factory=dict,
        description="Mapping of entity types to fields that should be deleted",
        example={
            StorageEntityTypeEnum.conversation: [ConversationFieldEnum.all],
            StorageEntityTypeEnum.conversation_space: [ConversationSpaceFieldEnum.all],
        },
    )

    @field_validator("save", "delete")
    @classmethod
    def validate_field_types(cls, value: dict[StorageEntityTypeEnum, list[FieldType]]) -> dict[StorageEntityTypeEnum, list[FieldType]]:
        """
        Validates that the fields match their corresponding storage entity types.

        Args:
            value: Dictionary mapping storage types to fields

        Returns:
            The validated dictionary

        Raises:
            ValueError: If field types don't match their storage entity type
        """
        for storage_type, fields in value.items():
            for field in fields:
                if storage_type == StorageEntityTypeEnum.conversation and not isinstance(field, ConversationFieldEnum):
                    raise ValueError(f"Field {field} is not valid for conversation storage type")

                elif storage_type == StorageEntityTypeEnum.conversation_node and not isinstance(field, ConversationNodeFieldEnum):
                    raise ValueError(f"Field {field} is not valid for conversation_node storage type")

                elif storage_type == StorageEntityTypeEnum.conversation_space and not isinstance(field, ConversationSpaceFieldEnum):
                    raise ValueError(f"Field {field} is not valid for conversation_space storage type")

        return value

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True
        json_schema_extra = {
            "examples": [
                {
                    "save": {
                        "conversation": ["title"],
                        "conversation_node": ["inputs", "outputs"],
                    },
                    "delete": {
                        "conversation": ["all"],
                        "conversation_space": ["all"],
                    },
                }
            ]
        }
