from dhenara.agent.client import Client
from dhenara.agent.types import FlowNodeInput, UserInput
from dhenara.agent.types.flow import Resource, ResourceObjectTypeEnum, ResourceQueryFieldsEnum
from shared_print_utils import print_content, print_error


def get_api_key():
    with open(".api_key.txt") as file:
        return file.read().strip()


api_key = get_api_key()

_refnum = "22187005"  # Non streaming


def main():
    client = Client(
        api_key=api_key,
        base_url="http://localhost:8000",
    )

    user_input = UserInput(
        content="What is ephatha.  Respond in 300 chars.",
        # content="Count 1 to 10 in words.",  # "When bible was written",
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
                query={ResourceQueryFieldsEnum.model_name: "gemini-1.5-pro"},
                # query={ResourceQueryFieldsEnum.model_name: "claude-3-5-haiku"},
                # query={ResourceQueryFieldsEnum.model_name: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"},
                # query={ResourceQueryFieldsEnum.model_name: "gpt-4o-mini"},
                # query={ResourceQueryFieldsEnum.model_name: "o3-mini"},
                # query={ResourceQueryFieldsEnum.model_name: "DeepSeek-R1"},
                # query={ResourceQueryFieldsEnum.model_name: "claude-3-7-sonnet"},
            ),
        ],
    )
    # Execute endpoint normally
    response = client.execute_endpoint(
        refnum=_refnum,
        node_input=node_input,
    )
    print_response_details(response)


# For non-streaming responses
def print_response_details(response):
    """Print the content from a non-streaming response"""
    if not response.is_success:
        print_error(response.first_message.message)
        return

    print("Assistant: ", end="", flush=True)

    for node_id, result in response.data.execution_results.items():
        print(f"\n\n🔸 Node ID: {node_id}")

        if result.node_output.data.response.status.successful:
            for choice in result.node_output.data.response.full_response.choices:
                for content_item in choice.contents:
                    print("\n")
                    text = content_item.get_text()
                    if text:
                        print_content(text, content_item.type)
        else:
            print_error(f"Node Execution Failed: {result.node_output.data.response.status}")

    print("\n")


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
