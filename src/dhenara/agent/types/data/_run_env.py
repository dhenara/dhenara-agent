from dataclasses import dataclass


@dataclass
class RunEnvParams:
    project_identifier: str
    agent_identifier: str
    run_id: str
    run_dir: str
    state_dir: str
    project_root: str
    outcome_dir: str
    outcome_repo_dir: str

    def get_template_variables(self) -> dict[str, str]:
        return {
            "dh_run_id": self.run_id,
            "dh_run_dir": str(self.run_dir),
            "dh_state_dir": str(self.state_dir),
            "dh_project_root": str(self.project_root),
        }
