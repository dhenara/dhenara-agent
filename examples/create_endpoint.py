import asyncio

from dhenara.client import Client
from dhenara.samples import STREAMING_CHATBOT_FLOW


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
        flow_data = {**STREAMING_CHATBOT_FLOW}

        # Create the flow
        # flow = client.create_flow(**flow_data)
        # print(f"Created flow: {flow.id}")

        # Create an endpoint with the flow
        response = client.create_endpoint(
            name="Production Chatbot Endpoint",
            flow_id=None,
            flow={**flow_data},
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
