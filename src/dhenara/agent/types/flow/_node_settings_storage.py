from typing import Union

from pydantic import Field, field_validator

from dhenara.agent.types.flow import (
    ConversationFieldEnum,
    ConversationNodeFieldEnum,
    ConversationSpaceFieldEnum,
    StorageEntityTypeEnum,
)
from dhenara.ai.types.shared.base import BaseModel

FieldType = Union[ConversationFieldEnum, ConversationNodeFieldEnum, ConversationSpaceFieldEnum]  # noqa: UP007


class StorageSettings(BaseModel):
    save: dict[
        StorageEntityTypeEnum | str,
        list[str | FieldType],
    ] = Field(
        default_factory=dict,
        description="Mapping of entity types to fields that should be saved",
    )

    delete: dict[
        StorageEntityTypeEnum | str,
        list[str | FieldType],
    ] = Field(
        default_factory=dict,
        description="Mapping of entity types to fields that should be deleted",
    )

    @field_validator("save", "delete")
    @classmethod
    def validate_field_types(
        cls,
        value: dict[
            StorageEntityTypeEnum | str,
            list[str | FieldType],
        ],
    ) -> dict[StorageEntityTypeEnum, list[FieldType]]:
        validated = {}

        for storage_type, fields in value.items():
            # Convert string storage_type to enum if needed
            if isinstance(storage_type, str):
                try:
                    storage_type = StorageEntityTypeEnum(storage_type)
                except ValueError:
                    raise ValueError(f"Invalid storage type: {storage_type}")

            # Convert string fields to appropriate enums
            validated_fields = []
            for field in fields:
                if isinstance(field, str):
                    if storage_type == StorageEntityTypeEnum.conversation:
                        field = ConversationFieldEnum(field)
                    elif storage_type == StorageEntityTypeEnum.conversation_node:
                        field = ConversationNodeFieldEnum(field)
                    elif storage_type == StorageEntityTypeEnum.conversation_space:
                        field = ConversationSpaceFieldEnum(field)
                validated_fields.append(field)

            # Validate field types
            for field in validated_fields:
                if storage_type == StorageEntityTypeEnum.conversation and not isinstance(field, ConversationFieldEnum):
                    raise ValueError(f"Field {field} is not valid for conversation storage type")
                elif storage_type == StorageEntityTypeEnum.conversation_node and not isinstance(
                    field, ConversationNodeFieldEnum
                ):
                    raise ValueError(f"Field {field} is not valid for conversation_node storage type")
                elif storage_type == StorageEntityTypeEnum.conversation_space and not isinstance(
                    field, ConversationSpaceFieldEnum
                ):
                    raise ValueError(f"Field {field} is not valid for conversation_space storage type")

            validated[storage_type] = validated_fields

        return validated
