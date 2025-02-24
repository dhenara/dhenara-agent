import logging

from dhenara.types.base import BaseModel
from dhenara.types.platform import FileContentFormatEnum, FileFormatEnum

logger = logging.getLogger(__name__)


# TODO: Need cleanup
# -----------------------------------------------------------------------------
class GenericFile(BaseModel):
    name: str
    metadata: dict | None = None


# -----------------------------------------------------------------------------
class LocalFile(GenericFile):
    url: str | None


# -----------------------------------------------------------------------------
class StoredFile(GenericFile):
    url: str | None


# -----------------------------------------------------------------------------
class ProcessedFile(GenericFile):
    processed_content: dict

    def get_source_file_name(self) -> str:
        """Get the original source file name"""
        return self.processed_content.get("name", "")

    def get_file_format(self) -> FileFormatEnum:
        """Get the file format enum"""
        format_str = self.processed_content.get("file_format", "")
        return FileFormatEnum(format_str)

    def get_content_format(self) -> FileContentFormatEnum:
        """Get the content format enum"""
        format_str = self.processed_content.get("content_format", "")
        return FileContentFormatEnum(format_str)

    def get_metadata(self) -> dict:
        """Get file metadata"""
        return self.processed_content.get("metadata", {})

    def get_mime_type(self) -> str | None:
        """Get the mime type of the file"""
        mime_type = self.get_metadata().get("mime_type")
        return mime_type.lower() if mime_type else None

    def get_processed_file_data(self, max_words: int | None = None) -> str:
        """Get processed file data with optional word limit"""
        content = str(self.processed_content.get("content", ""))
        if max_words:
            words = content.split()
            content = " ".join(words[:max_words])
        return content

    # -------------------------------------------------------------------------
    def get_processed_file_data_content_only(self):
        if self.processed_content:
            content_str = self.processed_content["content"]
            return content_str
        else:
            return ""
