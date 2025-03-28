import asyncio

from legacy_flow import chatbot_with_summarizer

from dhenara.agent.client import Client


def get_api_key():
    with open(".api_key.txt") as file:
        return file.read().strip()


api_key = get_api_key()


async def main():
    client = Client(
        api_key=api_key,
        base_url="http://localhost:8000",
    )

    try:
        # agent_data = {**chatbot_streaming_json}
        agent_data = chatbot_with_summarizer

        # Create the agent
        # agent = client.create_agent(**agent_data)
        # print(f"Created agent: {agent.id}")

        # Create an endpoint with the agent
        response = client.create_endpoint(
            name="Production Chatbot Endpoint",
            # agent_id=None,
            # agent={**agent_data},
            agent=agent_data.model_dump(),
            description="Endpoint for production chatbot",
            allowed_domains=["localhost:8000"],
        )

        if response.is_success:
            endpoint = response.data
            print(f"Endpoint created with reference number {endpoint.reference_number}: Endpoint is : {endpoint}")
        else:
            print(f"Failed to create endpoint: {response.first_message.message}")

    except Exception as e:
        print(f"Development setup failed: {e}")
    finally:
        await client.__aexit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(main())
