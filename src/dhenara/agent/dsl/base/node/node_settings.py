from pydantic import Field

from dhenara.agent.types.base import BaseEnum, BaseModel
from dhenara.ai.types.genai.dhenara.request import TextTemplate


class NodeSettings(BaseModel):
    """Node Settings."""

    pass


class RecordFileFormatEnum(BaseEnum):
    json = "json"
    yaml = "yaml"
    text = "text"
    binary = "binary"


class RecordSettingsItem(BaseModel):
    """Node Output Settings."""

    enabled: bool = Field(
        default=True,
        description="Save record or not",
    )
    path: str | TextTemplate = Field(
        ...,
        description="Path within run directory. Default is $var{node_id}",
    )
    filename: str | TextTemplate = Field(
        ...,
        description="Filename of record",
    )
    file_format: RecordFileFormatEnum = Field(
        ...,
        description="File format. Use `text` to dump as string. Default is `json`",
    )


DEFAULT_RESULT_RECORD_SETTINGS = RecordSettingsItem(
    enabled=True,
    path="$var{node_hier}/",  # Use node_hier instead of node_id
    filename="result.json",
    file_format=RecordFileFormatEnum.json,
)

DEFAULT_OUTCOME_RECORD_SETTINGS = RecordSettingsItem(
    enabled=True,
    path="$var{node_hier}/",  # Use node_hier instead of node_id
    filename="outcome.json",
    file_format=RecordFileFormatEnum.json,
)


class NodeRecordSettings(BaseModel):
    result: RecordSettingsItem = Field(
        default_factory=lambda: DEFAULT_RESULT_RECORD_SETTINGS.model_copy(deep=True),
        description="Record settings for comprehensive Node-Execution-Result",
    )
    outcome: RecordSettingsItem | None = Field(
        default_factory=lambda: DEFAULT_OUTCOME_RECORD_SETTINGS.model_copy(deep=True),
        description="Record settings for focused outcome",
    )

    @classmethod
    def with_outcome_format(
        cls,
        file_format: RecordFileFormatEnum,
    ) -> "NodeRecordSettings":
        """Factory method to easily create settings with custom outcome configuration."""
        return DEFAULT_OUTCOME_RECORD_SETTINGS.model_copy(
            deep=True,
            update={file_format: file_format},
        )
