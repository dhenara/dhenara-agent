import asyncio

from dhenara.client import Client
from dhenara.samples.flows import SIMPLE_CHATBOT_FLOW
from dhenara.types import FlowExecutionStatus


def get_api_key():
    with open(".api_key.txt") as file:
        return file.read().strip()


api_key = get_api_key()
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

        # Create an endpoint with the flow
        response = client.create_endpoint(
            name="Production Chatbot Endpoint",
            flow_id=None,
            flow={**flow_data},
            description="Endpoint for production chatbot",
            allowed_domains=["api.mychatbot.com"],
        )

        if response.is_success:
            endpoint = response.data
            print(f"Endpoint created: {endpoint.id}")
        else:
            print(f"Failed to create endpoint: {response.first_message.message}")

        ## List all endpoints
        # endpoints = client.list_endpoints(workspace_id=workspace_id)
        # print(f"Available endpoints: {json.dumps(endpoints, indent=2)}")
    except Exception as e:
        print(f"Development setup failed: {e}")
    finally:
        await client.__aexit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(main())


async def main():
    async with Client(api_key="your-api-key") as client:
        # Execute flow normally
        response = await client.execute_flow_async(
            flow_id="flow123",
            input_data={"prompt": "Hello"},
        )

        if response.is_success:
            execution = response.data
            print(f"Execution ID: {execution.execution_id}")
            print(f"Status: {execution.status}")
        else:
            print(f"Error: {response.first_message.message}")

        # Execute flow with streaming
        async for chunk in await client.execute_flow_async(
            flow_id="flow123",
            input_data={"prompt": "Hello"},
            stream=True,
        ):
            print(chunk.decode(), end="", flush=True)

        # Check status
        status_response = await client.get_flow_status_async("execution123")
        if status_response.is_success:
            status = status_response.data
            print(f"Execution status: {status.status}")
            if status.status == FlowExecutionStatus.COMPLETED:
                print(f"Result: {status.result}")
            elif status.status == FlowExecutionStatus.FAILED:
                print(f"Error: {status.error}")
