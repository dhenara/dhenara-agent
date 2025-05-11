from dataclasses import dataclass


@dataclass
class RunEnvParams:
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
