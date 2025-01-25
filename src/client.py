class Client:
    def __init__(self, api_key: str, environment: str = "production"):
        self.api_key = api_key
        self.environment = environment

    async def execute_flow(self, flow_config: dict, input_data: dict):
        pass
