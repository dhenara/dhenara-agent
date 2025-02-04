import asyncio

from dhenara.client import Client
from dhenara.types import FlowExecutionStatusEnum


def get_api_key():
    with open(".api_key.txt") as file:
        return file.read().strip()


api_key = get_api_key()


async def main():
    async with Client(
        api_key=api_key,
        base_url="http://localhost:8000",
    ) as client:
        flow_id = ("flow123",)

        # Execute flow with streaming
        async for chunk in await client.execute_flow_async(
            flow_id=flow_id,
            input_data={"prompt": "Hello"},
            stream=True,
        ):
            print(chunk.decode(), end="", flush=True)

        # Check status
        status_response = await client.get_flow_status_async("execution123")
        if status_response.is_success:
            status = status_response.data
            print(f"Execution status: {status.status}")
            if status.status == FlowExecutionStatusEnum.COMPLETED:
                print(f"Result: {status.result}")
            elif status.status == FlowExecutionStatusEnum.FAILED:
                print(f"Error: {status.error}")


if __name__ == "__main__":
    asyncio.run(main())
