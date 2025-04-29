import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path

import yaml
from pydantic import Field

from dhenara.agent.types.base import BaseModel

logger = logging.getLogger(__name__)


class _GlobalConfigData(BaseModel):
    """
    Base configuration model with all possible settings.

    This model defines all configuration parameters that can be set throughout
    the application. It provides defaults for all values.
    """

    # API Keys and endpoints
    api_keys: dict[str, str] = Field(
        default_factory=dict,
        description="Dhenara API keys",
    )
    endpoints: dict[str, str] = Field(
        default_factory=dict,
        description="Dhenara API endpoints",
    )
    ep_version: str | None = Field(
        "v1",
        description="Dhenara API endpoint version",
    )

    # Default model settings
    # default_model: str = Field("gpt-4o-mini", description="Default model to use when none is specified")
    # model_options: Dict[str, Dict[str, Any]] = Field(
    #    default_factory=dict, description="Default options for different models"
    # )

    # Resource  fil pathe
    resource_paths: dict[str, str] = Field(
        default_factory=dict,
        description="Paths to resource files",
    )

    # Execution settings
    timeout: int = Field(
        60,
        description="Default timeout in seconds for API calls",
    )
    max_retries: int = Field(
        3,
        description="Default maximum retries for API calls",
    )

    # Logging configuration
    log_level: str = Field(
        "INFO",
        description="Default logging level",
    )
    log_file: str | None = Field(
        None,
        description="Path to log file, if any",
    )

    # Environment
    environment: str = Field(
        "development",
        description="Current execution environment (development, production, etc.)",
    )

    class Config:
        extra = "allow"  # Allow additional fields for flexibility


class ConfigurationContext:
    """
    Thread-local configuration context manager.

    This class manages global and thread-local configurations for the Dhenara package.
    It provides methods to load configs from files, set/get values, and temporarily
    override settings.

    Usage examples:
        # Set configuration values
        ConfigurationContext.initialize(api_keys={"openai": "sk-..."})

        # Load from file
        ConfigurationContext.load_config("config.yaml", env="production")

        # Access current configuration
        config = ConfigurationContext.get_config()

        # Temporarily override settings
        with ConfigurationContext.config_override(timeout=120):
            # Do something with the temporary settings
            pass
    """

    # Global configuration shared across all threads
    _global_config = _GlobalConfigData()

    # Thread-local storage for thread-specific configurations
    _thread_local = threading.local()

    # Track which config files were loaded
    _loaded_files: set[str] = set()

    @classmethod
    def initialize(cls, **kwargs) -> None:
        """
        Initialize the global configuration with provided values.

        This should typically be called once at application startup.

        Args:
            **kwargs: Configuration key-value pairs to set
        """
        config_data = cls._global_config.model_dump()
        config_data.update(kwargs)
        cls._global_config = _GlobalConfigData.model_validate(config_data)

    @classmethod
    def get_config(cls) -> _GlobalConfigData:
        """
        Get the current configuration.

        Returns the thread-local configuration if it exists,
        otherwise returns the global configuration.

        Returns:
            _GlobalConfigData: The current configuration
        """
        if hasattr(cls._thread_local, "config"):
            return cls._thread_local.config
        return cls._global_config

    @classmethod
    def set_thread_config(cls, config: _GlobalConfigData) -> None:
        """
        Set thread-local configuration.

        Args:
            config: Configuration object to set for this thread
        """
        cls._thread_local.config = config

    @classmethod
    def reset_thread_config(cls) -> None:
        """
        Reset thread-local configuration.

        This removes any thread-specific configuration, reverting
        back to the global configuration.
        """
        if hasattr(cls._thread_local, "config"):
            delattr(cls._thread_local, "config")

    @classmethod
    @contextmanager
    def config_override(cls, **kwargs):
        """
        Context manager for temporarily overriding configuration values.

        This creates a thread-local copy of the current configuration,
        applies the overrides, and restores the previous configuration
        when the context ends.

        Args:
            **kwargs: Configuration values to override

        Example:
            with ConfigurationContext.config_override(timeout=120):
                # Code here will use a timeout of 120 seconds
                client.make_request()
            # Code here will use the original timeout value
        """
        old_config = cls.get_config()
        thread_config = old_config.model_copy(deep=True)

        # Update with new values
        config_dict = thread_config.model_dump()
        config_dict.update(kwargs)
        thread_config = _GlobalConfigData.model_validate(config_dict)

        cls.set_thread_config(thread_config)
        try:
            yield
        finally:
            cls.reset_thread_config()

    @classmethod
    def load_config(cls, path: str | Path | None = None, env: str | None = None) -> None:
        """
        Load configuration from a YAML file.

        Searches for configuration files in the following order:
        1. Specified path (if provided)
        2. ~/.dhenara/config.yaml
        3. ./config.yaml

        Args:
            path: Optional specific path to a config file
            env: Optional environment name to load environment-specific config

        Example:
            # Load configuration for the production environment
            ConfigurationContext.load_config(env="production")

            # Load from a specific file
            ConfigurationContext.load_config("my_config.yaml")
        """
        # Default paths
        paths_to_try = [
            Path(os.path.expanduser("~/.dhenara/config.yaml")),
            Path("./config.yaml"),
        ]

        # Add specified path if provided
        if path:
            path = Path(path)
            paths_to_try.insert(0, path)

        for config_path in paths_to_try:
            if config_path.exists() and str(config_path) not in cls._loaded_files:
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)

                # Handle environment-specific configuration
                if env and env in config_data:
                    # Merge env-specific with base, with env taking precedence
                    base_config = {k: v for k, v in config_data.items() if k != env}
                    env_config = config_data[env]
                    config_data = {**base_config, **env_config}

                # Update global config
                # Merge with existing config rather than replacing
                existing_config = cls._global_config.model_dump()
                merged_config = {**existing_config, **config_data}
                cls._global_config = _GlobalConfigData.model_validate(merged_config)
                cls._loaded_files.add(str(config_path))
                return

        # If no file was found and loaded, keep existing configuration


# Initialize configuration with defaults (empty config)
# Applications should call load_config() or initialize() during startup
config = ConfigurationContext.get_config()


# Simple accessor functions
def get_config() -> _GlobalConfigData:
    """
    Get the current configuration.

    This is a convenience function that delegates to ConfigurationContext.get_config().

    Returns:
        _GlobalConfigData: The current configuration object
    """
    return ConfigurationContext.get_config()


# Export the context manager for temporary overrides
config_override = ConfigurationContext.config_override
