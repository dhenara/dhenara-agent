import os


class IsolatedExecution:
    """Provides an isolated execution environment for agents."""

    def __init__(self, run_context):
        self.run_context = run_context
        self.temp_env = {}

    async def __aenter__(self):
        """Set up isolation environment."""
        # Save current environment variables to restore later
        self.temp_env = os.environ.copy()

        # Set environment variables for the run
        os.environ["DHENARA_RUN_ID"] = self.run_context.run_id
        os.environ["DHENARA_INPUT_DIR"] = str(self.run_context.input_dir)
        os.environ["DHENARA_OUTPUT_DIR"] = str(self.run_context.output_dir)

        # Set up working directory isolation
        os.chdir(self.run_context.input_dir)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up isolation environment."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.temp_env)

        # Return to original directory
        os.chdir(self.run_context.project_root)

    async def run(self, agent_module, input_data):
        """Run the agent in the isolated environment."""
        # TODO
        # Set up logging for this run
        # log_file = self.run_context.state_dir / "execution.log"
        # TODO setup_logging(log_file)

        # Execute the agent
        try:
            result = await agent_module.run(input_data)
            return result
        except Exception as e:
            # logging.exception(f"Agent execution failed: {e}")
            raise e
