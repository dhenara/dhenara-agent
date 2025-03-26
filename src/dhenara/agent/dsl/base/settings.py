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
    git_commit: bool | None = Field(
        default=None,
        description="Commot or not, if applicable to record",
    )
    git_commit_message: str | TextTemplate | None = Field(
        default=None,
        description="Commot or not, if applicable to record",
    )


DEFAULT_INPUT_RECORD_SETTINGS = RecordSettingsItem(
    enabled=True,
    path="${run_id}/input/",
    filename="${node_id}.json",
    file_format=RecordFileFormatEnum.json,
    git_commit=None,
    git_commit_message=None,
)
DEFAULT_OUPUT_RECORD_SETTINGS = default = RecordSettingsItem(
    enabled=True,
    path="${run_id}/output/",
    filename="${node_id}.json",
    file_format=RecordFileFormatEnum.json,
    git_commit=None,
    git_commit_message=None,
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
        default=None,
        description="Outcome record settings",
    )

    @classmethod
    def with_outcome(
        cls,
        path: str,
        filename: str,
        file_format: str = "json",
        git_commit: bool = True,
        git_commit_message: str | None = None,
    ) -> "NodeRecordSettings":
        """Factory method to easily create settings with an outcome configuration."""
        return cls(
            outcome=RecordSettingsItem(
                path=path,
                filename=filename,
                file_format=file_format,
                git_commit=git_commit,
                git_commit_message=git_commit_message,
            )
        )

    @classmethod
    def with_custom_output(
        cls, path: str, filename: str, file_format: str = "json", git_commit: bool = False
    ) -> "NodeRecordSettings":
        """Factory method to easily create settings with custom output configuration."""
        return cls(
            output=RecordSettingsItem(
                path=path,
                filename=filename,
                file_format=file_format,
                git_commit=git_commit,
            )
        )
