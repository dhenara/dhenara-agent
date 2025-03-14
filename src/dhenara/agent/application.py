#  Main file in an app
# TODO: Move to template

import logging

from dhenara.agent.config import ConfigurationContext
from dhenara.agent.resource.registry import resource_config_registry
from dhenara.ai.types import ResourceConfig

# Step 1: Set up logging
logging.basicConfig(level=logging.DEBUG)


# Step 2: Initialize configuration
def initialize_app():
    """Initialize the application with configuration and resources."""
    # Load configuration from file with environment-specific settings
    ConfigurationContext.load_config("config.yaml", env="production")

    # Or set configuration programmatically
    ConfigurationContext.initialize(
        api_keys={
            "dhenara": "dh-your-api-key",
        },
        timeout=60,
        max_retries=3,
    )

    # Populate standard resource registries
    # Most of the application need only standard reristries, but ou can create additional, if you need

    # Register some resources
    # gpt4_model = AIModel(name="gpt-4o", provider="openai")
    # model_registry.register("gpt4", gpt4_model)

    # Load resource configuration
    default_resource_config = ResourceConfig()
    default_resource_config.load_from_file("~/.env_keys/.dhenara_credentials.yaml", init_endpoints=True)

    # Every registry need at least one with name  `default`
    resource_config_registry.register(
        "default",
        default_resource_config,
    )

    # If you created additional registries, those need to be exposed to the application
    # return {"my_custom_registry_1": my_custom_registry_1, "my_custom_registry_2": my_custom_registry_}


# Step 3: call init fn
app_registries = initialize_app()
# Make custom  registries available to the application, if you created them
# my_custom_registry_1= app_registries["my_custom_registry_1"]
