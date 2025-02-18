from dhenara.client import Client
from dhenara.types import FlowNodeInput, UserInput
from dhenara.types.flow import Resource, ResourceObjectTypeEnum


def get_api_key():
    with open(".api_key.txt") as file:
        return file.read().strip()


api_key = get_api_key()

_refnum = "22121349"  # Non streaming


def main():
    client = Client(
        api_key=api_key,
        base_url="http://localhost:8000",
    )

    user_input = UserInput(
        content="What is ephatha.  Respond in 300 chars.",
    )
    # node_input = FlowNodeInput(
    #    user_input=user_input,
    # )
    node_input = FlowNodeInput(
        user_input=user_input,
        resources=[
            Resource(
                object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                object_id=None,
                query={"ai_model__api_model_name": "gemini-1.5-pro-002"},
                # query={"ai_model__api_model_name": "claude-3-5-haiku-20241022"},
                # query={"ai_model__api_model_name": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"},
                # query={"ai_model__api_model_name": "gpt-4o-mini"},
            ),
        ],
    )
    # Execute endpoint normally
    response = client.execute_endpoint(
        refnum=_refnum,
        node_input=node_input,
    )

    print(f'AJJ: reponse is"\n\n{response}\n\n')
    if response.is_success:
        # print(f"Resposne is: {response}")
        print("\n")
        print(f"--------Status: {response.data.execution_status}--------\n")
        print("--------Node Outputs are --------\n")
        for node_id, result in response.data.execution_results.items():
            print(f"{node_id}:")
            if result.node_output.data.response.status.successful:
                print(f"{result.node_output.data.response.full_response.choices[0]}")
            else:
                print(f"{result.node_output.data.response.status}")
            print("\n")
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
