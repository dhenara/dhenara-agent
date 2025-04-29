from urllib.parse import urljoin, urlsplit

from pydantic import Field, field_validator

from dhenara.agent.types.base import BaseModel


class UrlSettings(BaseModel):
    """Settings for managing API URL paths and configurations.

    This model handles the creation and management of URL paths for different
    API endpoints, ensuring proper formatting and validation of URLs.

    Attributes:
        app_route: The base application route segment.
        devtime_route: The development-time route segment.
        runtime_route: The runtime route segment.
    """

    base_url: str = Field(
        description="Base url",
    )
    ep_version: str | None = Field(
        description="version string in url",
    )
    app_route: str = Field(
        default="api",
        description="Base application route segment",
    )
    devtime_route: str = Field(
        default="run/dev/",
        description="Development-time route segment",
    )
    runtime_route: str = Field(
        default="run/serve/",
        description="Runtime route segment",
    )

    @field_validator("base_url", "app_route", "devtime_route", "runtime_route")
    @classmethod
    def clean_route(cls, value: str) -> str:
        """Clean route segments by removing leading/trailing slashes."""
        return value.strip("/")

    def get_path_url(self, url_name: str) -> str | None:
        """Generate a path URL based on the specified URL type."""

        url_mapping = {
            "devtime_dhenrun_ep": f"{self.app_route}/{self.devtime_route}/run-endpoint/",
            "runtime_dhenrun_ep": f"{self.app_route}/{self.runtime_route}/run-endpoint/",
        }

        if url_name not in url_mapping:
            raise ValueError(f"URL not found for {url_name}")

        return url_mapping[url_name]

    def get_full_url(self, url_name: str) -> str:
        """Construct a full URL by combining base URL with path URL."""

        # Validate and clean base_url
        cleaned_base = self.base_url.rstrip("/")
        if not urlsplit(cleaned_base).scheme:
            raise ValueError("Invalid base URL: missing scheme (http:// or https://)")

        version_str = f"{self.ep_version}" if self.ep_version else ""
        path_url = self.get_path_url(url_name)
        return urljoin(f"{cleaned_base}/{version_str}/", path_url)

    class Config:
        """Pydantic model configuration."""

        frozen = True  # Make the settings immutable
        str_strip_whitespace = True
