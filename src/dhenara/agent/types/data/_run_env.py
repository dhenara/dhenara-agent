from pydantic import Field

from dhenara.agent.types.base import BaseModel

from ._observability import ObservabilitySettings


class RunEnvParams(BaseModel):
    """
    Parameters for a specific run environment, used in template rendering and artifact management.
    """

    run_id: str
    run_dir: str
    run_root: str
    run_root_subpath: str | None
    effective_run_root: str
    trace_dir: str
    outcome_repo_dir: str | None = None


class AgentRunConfig(BaseModel):
    """Configuration for agent run execution."""

    # TODO: Below configs are not taken care. Modify run context to use RunConfig
    root_component_id: str | None = None
    project_root: str | None = None
    run_root: str | None = None
    run_root_subpath: str | None = None
    run_id: str | None = None
    observability_settings: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    # - For Rerurns
    previous_run_id: str | None = None
    start_hierarchy_path: str | None = None
    run_id_prefix: str | None = None
