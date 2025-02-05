from dhenara.client import Client
from dhenara.types import FlowNodeInput, UserInput


def get_api_key():
    with open(".api_key.txt") as file:
        return file.read().strip()


api_key = get_api_key()

_refnum = "22169394"  #  "22182349"


def main():
    client = Client(
        api_key=api_key,
        base_url="http://localhost:8000",
    )

    user_input = UserInput(
        content="When bible was written",  # "What is ephatha",
    )
    node_input = FlowNodeInput(user_input=user_input)
    # Execute endpoint normally
    response = client.execute_endpoint(
        refnum=_refnum,
        node_input=node_input,
    )

    if response.is_success:
        # execution = response.data
        print(f"Resposne is: {response}")
    else:
        print(f"Error: {response.first_message.message}")


if __name__ == "__main__":
    main()

"""
async def main():
    async with Client(
        api_key=api_key,
        base_url="http://localhost:8000",
    ) as client:
        endpoint_id = ("endpoint123",)

        # Execute endpoint normally
        response = await client.execute_endpoint_async(
            endpoint_id=endpoint_id,
            input_data={"prompt": "What is ephatha?"},
        )

        if response.is_success:
            execution = response.data
            print(f"Execution ID: {execution.execution_id}")
            print(f"Status: {execution.status}")
        else:
            print(f"Error: {response.first_message.message}")


if __name__ == "__main__":
    asyncio.run(main())
"""
