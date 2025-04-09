import os

from dhenara.agent.run import RunContext


class IsolatedExecution:
    """Provides an isolated execution environment for agents."""

    def __init__(self, run_context):
        self.run_context: RunContext = run_context
        self.temp_env = {}

    async def __aenter__(self):
        """Set up isolation environment."""
        # Save current environment variables to restore later
        self.temp_env = os.environ.copy()

        # Set environment variables for the run
        # TODO_FUTURE
        # os.environ["DHENARA_RUN_ID"] = self.run_context.run_id
        # os.environ["DHENARA_RUN_ROOT"] = str(self.run_context.run_root)

        # Set up working directory isolation
        os.chdir(self.run_context.run_dir)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up isolation environment."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.temp_env)

        # Return to original directory
        os.chdir(self.run_context.project_root)

    async def run(
        self,
        runner,
    ):
        """Run the agent in the isolated environment."""
        # Execute the agent
        try:
            result = await runner.run()

            from dhenara.agent.observability import force_flush_logging, force_flush_metrics, force_flush_tracing

            force_flush_tracing()
            force_flush_metrics()
            force_flush_logging()

            return result
        except Exception as e:
            # logging.exception(f"Agent execution failed: {e}")
            raise e
