import os

from dhenara.agent.run import RunContext
from dhenara.agent.types.flow import NodeInputs


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

    async def run(self, agent_module, run_context: RunContext, initial_inputs: NodeInputs):
        """Run the agent in the isolated environment."""
        # TODO
        # Set up logging for this run
        # log_file = self.run_context.state_dir / "execution.log"
        # TODO setup_logging(log_file)

        # Execute the agent
        try:
            result = await agent_module.run(
                run_context=run_context,
                initial_inputs=initial_inputs,
            )
            return result
        except Exception as e:
            # logging.exception(f"Agent execution failed: {e}")
            raise e
