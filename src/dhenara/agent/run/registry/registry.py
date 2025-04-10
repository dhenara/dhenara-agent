"""
Global registry access module for Dhenara.

This module provides access to the standard registries used throughout
the Dhenara package. Most applications should import registries from
this module rather than creating their own.
"""

from typing import Any

from dhenara.ai.types import AIModel, ResourceConfig

from ._resource_registry import ResourceRegistry

# Standard registries
model_registry = ResourceRegistry[AIModel](AIModel, name="AIModel")
resource_config_registry = ResourceRegistry[ResourceConfig](ResourceConfig, name="ResourceConfig")

# Initialize with empty values - applications will populate these
_registries_initialized = False


def initialize_registries(resources: dict[str, Any] | None = None) -> None:
    """
    Initialize all standard registries with provided resources.

    This should be called once during application startup.

    Args:
        resources: Dictionary of resources to register, where keys are
                 registry names and values are dictionaries mapping
                 resource names to resource instances

    Example:
        initialize_registries({
            "AIModel": {
                "gpt4": gpt4_model,
                "claude": claude_model
            },
            "ResourceConfig": {
                "default": my_resource_config
            }
        })
    """
    global _registries_initialized

    if resources:
        for registry_name, items in resources.items():
            if registry_name == "AIModel":
                for name, resource in items.items():
                    model_registry.register(name, resource)
            elif registry_name == "ResourceConfig":
                for name, resource in items.items():
                    resource_config_registry.register(name, resource)

    _registries_initialized = True
