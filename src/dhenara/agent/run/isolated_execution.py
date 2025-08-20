import contextlib
import os

from dhenara.agent.run import RunContext


class IsolatedExecution:
    """
    Lightweight execution context.
    Changes from previous (unsafe) version:
      - No full env wipe/restore (only overlay chosen vars)
      - No global chdir by default (agents should use absolute paths)
      - Revert only what we modify
    """

    def __init__(self, run_context: RunContext, *, change_dir: bool = False, inject_env: dict | None = None):
        self.run_context: RunContext = run_context
        self.change_dir = change_dir
        self.inject_env = inject_env or {}
        self._orig_cwd: str | None = None
        self._env_prev: dict[str, str] = {}
        self._unset_keys: set[str] = set()

    async def __aenter__(self):
        for k, v in self.inject_env.items():
            if k in os.environ:
                self._env_prev[k] = os.environ[k]
            else:
                self._unset_keys.add(k)
            os.environ[k] = v
        if self.change_dir:
            self._orig_cwd = os.getcwd()
            os.chdir(self.run_context.run_dir)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._orig_cwd:
            with contextlib.suppress(Exception):
                os.chdir(self._orig_cwd)
        for k, v in self._env_prev.items():
            os.environ[k] = v
        for k in self._unset_keys:
            os.environ.pop(k, None)

    async def run(self, runner):
        # Run the agent in the isolated environment.
        try:
            result = await runner.run()
            from dhenara.agent.observability import (
                force_flush_logging,
                force_flush_metrics,
                force_flush_tracing,
            )

            force_flush_tracing()
            force_flush_metrics()
            force_flush_logging()
            return result
        except Exception:
            raise
