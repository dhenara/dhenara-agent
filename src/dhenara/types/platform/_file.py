from dhenara.types.base import BaseModel
from dhenara.types.platform import FileContentFormatEnum, FileFormatEnum


# -----------------------------------------------------------------------------
class GenericFile(BaseModel):
    url: str | None
    processed_content: dict | str

    def get_content(self):
        return str(self.content)

    # -------------------------------------------------------------------------
    def get_source_file_name(self):
        return self.processed_content["name"] or ""

    # -------------------------------------------------------------------------
    def get_file_format(self) -> FileFormatEnum:
        format_str = self.processed_content["file_format"] or ""
        return FileFormatEnum(format_str)

    # -------------------------------------------------------------------------
    def get_content_format(self) -> FileContentFormatEnum:
        format_str = self.processed_content["content_format"]
        return FileContentFormatEnum(format_str)

    # -------------------------------------------------------------------------
    def get_metadata(self):
        return self.processed_content.get("metadata", {})

    # -------------------------------------------------------------------------
    def get_mime_type(self) -> str | None:
        mime_type = self.get_metadata().get("mime_type", None)
        return mime_type.lower() or None

    # -------------------------------------------------------------------------
    def get_processed_file_data(self, max_words: int | None):
        if self.processed_content:
            # file_content = FileContentData(**self.processed_content)
            # file_content = dict_to_dataclass(dataclass_type=FileContentData, data=self.processed_content)

            content_str = str(self.processed_content)
            words = content_str.split()
            # Return the content limited to max_words number of words
            return " ".join(words[:max_words])
        else:
            return ""

    # -------------------------------------------------------------------------
    def get_processed_file_data_content_only(self):
        if self.processed_content:
            content_str = self.processed_content["content"]
            return content_str
        else:
            return ""
