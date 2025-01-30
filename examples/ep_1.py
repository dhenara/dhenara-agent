import asyncio
import json

from dhenara.client import Client
from dhenara.samples.flows import SIMPLE_CHATBOT_FLOW

# TODO
api_key = "abcdefghijk"
workspace_id = "aaa"


async def main():
    # Create developer client
    client = Client(
        api_key=api_key,
        base_url="http://localhost:8000",
    )

    # TODO: delete
    client._set_credentials(
        customer_id="abd_customer",
        workspace_id=workspace_id,
        endpoint_id=None,
        credentials_token=None,
    )

    try:
        flow_data = {**SIMPLE_CHATBOT_FLOW}

        # Create the flow
        # flow = client.create_flow(**flow_data)
        # print(f"Created flow: {flow.id}")

        # Create an endpoint for the flow
        endpoint = client.create_endpoint(
            name="Production Chatbot Endpoint",
            flow_id=None,
            flow={**flow_data},
            description="Endpoint for production chatbot",
            allowed_domains=["api.mychatbot.com"],
        )
        print(f"Created endpoint: {endpoint['reference_number']}")

        # List all endpoints
        endpoints = client.list_endpoints(workspace_id=workspace_id)
        print(f"Available endpoints: {json.dumps(endpoints, indent=2)}")

    except Exception as e:
        print(f"Development setup failed: {e}")
    finally:
        await client.__aexit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(main())
