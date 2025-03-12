"""
{{agent_name}}

{{agent_description}}
"""



class Agent:
    """{{agent_name}} agent implementation."""

    def __init__(self, config=None):
        """Initialize the agent with optional configuration."""
        self.config = config or {}
        self.client = None
        self.setup()

    def setup(self):
        """Set up any resources needed by the agent."""
        # Initialize AI model client if needed
        # self.client = AIModelClient(...)
        pass

    async def process(self, query, context=None):
        """
        Process a query with this agent.

        Args:
            query: The user's query
            context: Optional context information

        Returns:
            The agent's response
        """
        # Example implementation
        if not self.client:
            return {"response": "Agent not properly initialized"}

        # Your agent logic here
        return {"response": f"Processed: {query}"}

    def cleanup(self):
        """Clean up any resources used by the agent."""
        if self.client:
            # await self.client.cleanup_async()
            pass
