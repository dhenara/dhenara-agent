import asyncio

from dhenara.client import Client, DhenaraAPIError, DhenaraConnectionError
from dhenara.samples.flows import SIMPLE_CHATBOT_FLOW

# Assuming the Client class and related exceptions have been imported from the SDK module
# from dhenara_sdk import Client, DhenaraAPIError, DhenaraConnectionError


# TODO
api_key = "abcdefghijk"
workspace_id = "aaa"


async def main():
    # Initialize the client
    client = Client(api_key="your-api-key")

    # Synchronous Operations
    try:
        # Create a client token
        token_response = client.create_client_token(domain="example.com")
        print("Client Token:", token_response)

        # Define a new flow
        flow_definition = {**SIMPLE_CHATBOT_FLOW}

        flow = client.define_flow(
            workspace_id=workspace_id,
            name="My Flow",
            definition=flow_definition,
            description="A simple AI model flow",
        )
        print("Defined Flow:", flow)

        # Execute the flow synchronously
        execution_result = client.execute_flow(
            flow_id=flow["id"],
            input_data={"prompt": "Hello, AI!"},
        )
        print("Execution Result:", execution_result)

        # Get flow execution status
        status = client.get_flow_status(execution_id=execution_result["execution_id"])
        print("Execution Status:", status)

    except (DhenaraAPIError, DhenaraConnectionError) as e:
        print(f"An error occurred: {e}")

    # Asynchronous Operations
    async with client:
        try:
            # Execute the flow asynchronously with streaming
            async for chunk in client.execute_flow_async(
                flow_id="flow-456",
                input_data={"prompt": "Hello, async AI!"},
                stream=True,
            ):
                print("Streamed Chunk:", chunk.decode())

            # Execute the flow asynchronously without streaming
            async_result = await client.execute_flow_async(
                flow_id="flow-456",
                input_data={"prompt": "Hello, async AI!"},
                stream=False,
            )
            print("Async Execution Result:", async_result)

            # Create a run endpoint asynchronously
            run_endpoint = await client.create_run_endpoint_async(
                workspace_id=workspace_id,
                name="Run Endpoint 1",
                flow_id="flow-456",
                allowed_domains=["example.com"],
            )
            print("Created Run Endpoint:", run_endpoint)

        except (DhenaraAPIError, DhenaraConnectionError) as e:
            print(f"An async error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
