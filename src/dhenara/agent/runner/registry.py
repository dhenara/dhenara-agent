# dhenara/agent/registry.py
import os
from pathlib import Path

import yaml

from dhenara.agent.types.agent import AgentDefinition

# TODO: Currently not used


class AgentRegistry:
    """Registry for managing agent definitions."""

    def __init__(self):
        self.agents: dict[str, AgentDefinition] = {}
        self.config_dir = os.path.expanduser("~/.dhenara/agents")
        os.makedirs(self.config_dir, exist_ok=True)

    def register_agent(self, name: str, agent_def: AgentDefinition) -> None:
        """Register an agent definition."""
        self.agents[name] = agent_def

        # Serialize to disk for persistence
        agent_path = Path(self.config_dir) / f"{name}.yaml"
        with open(agent_path, "w") as f:
            yaml.dump(agent_def.model_dump(), f)

    def get_agent(self, name: str) -> AgentDefinition | None:
        """Get an agent definition by name."""
        # Check memory first
        if name in self.agents:
            return self.agents[name]

        # Look on disk
        agent_path = Path(self.config_dir) / f"{name}.yaml"
        if agent_path.exists():
            with open(agent_path) as f:
                agent_data = yaml.safe_load(f)
                agent_def = AgentDefinition.model_validate(agent_data)
                self.agents[name] = agent_def
                return agent_def

        return None


# Global registry instance
agent_registry = AgentRegistry()


def load_agent_definition(name: str) -> AgentDefinition:
    """Utility function to load an agent definition."""
    agent = agent_registry.get_agent(name)
    if not agent:
        raise ValueError(f"Agent '{name}' not found in registry")
    return agent
