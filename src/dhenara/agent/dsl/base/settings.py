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
        default="${node_id}",
        description="Path within record's parent. Default is node_id",
    )
    filename: str | TextTemplate = Field(
        default="${node_id}.json",
        description="Filename of record. Default is node_id.json",
    )
    file_format: RecordFileFormatEnum = Field(
        ...,
        description="File format. Use text to dump as string",
    )


DEFAULT_INPUT_RECORD_SETTINGS = RecordSettingsItem(
    enabled=True,
    path="${run_id}/${node_id}/",
    filename="input.json",  # "{node_id}.json",
    file_format=RecordFileFormatEnum.json,
)
DEFAULT_OUPUT_RECORD_SETTINGS = default = RecordSettingsItem(
    enabled=True,
    path="${run_id}/${node_id}/",
    filename="output.json",
    file_format=RecordFileFormatEnum.json,
)
DEFAULT_OUTCOME_RECORD_SETTINGS = default = RecordSettingsItem(
    enabled=True,
    path="${run_id}/${node_id}/",
    filename="outcome.json",
    file_format=RecordFileFormatEnum.json,
)


class NodeRecordSettings(BaseModel):
    input: RecordSettingsItem = Field(
        default_factory=lambda: DEFAULT_INPUT_RECORD_SETTINGS.model_copy(deep=True),
        description="Input record settings",
    )
    output: RecordSettingsItem = Field(
        default_factory=lambda: DEFAULT_OUPUT_RECORD_SETTINGS.model_copy(deep=True),
        description="Output record settings",
    )
    outcome: RecordSettingsItem | None = Field(
        default_factory=lambda: DEFAULT_OUTCOME_RECORD_SETTINGS.model_copy(deep=True),
        description="Outcome record settings",
    )

    @classmethod
    def with_outcome_format(
        cls,
        file_format: RecordFileFormatEnum,
    ) -> "NodeRecordSettings":
        """Factory method to easily create settings with custom outcome configuration."""
        return cls(
            outcome=RecordSettingsItem(
                file_format=file_format,
            )
        )


class GitSettingsItem(BaseModel):
    """Node Output Settings."""

    path: str | TextTemplate = Field(
        ...,
        description="Path within repo",
    )
    filename: str | TextTemplate = Field(
        ...,
        description="Filename ",
    )
    commit: bool | None = Field(
        default=None,
        description="Commot or not, if applicable to record",
    )
    commit_message: str | TextTemplate | None = Field(
        default=None,
        description="Commot or not, if applicable to record",
    )


class NodeGitSettings(BaseModel):
    input: GitSettingsItem | None = Field(
        default=None,
        description="Input git settings",
    )
    output: GitSettingsItem | None = Field(
        default=None,
        description="Output git settings",
    )
    outcome: GitSettingsItem | None = Field(
        default=None,
        description="Outcome git settings",
    )

    @classmethod
    def with_outcome(
        cls,
        path: str,
        filename: str,
        commit: bool,
        commit_message: str | None = None,
    ) -> "NodeGitSettings":
        """Factory method to easily create settings with an outcome configuration."""
        return cls(
            outcome=GitSettingsItem(
                path=path,
                filename=filename,
                commit=commit,
                commit_message=commit_message,
            )
        )
