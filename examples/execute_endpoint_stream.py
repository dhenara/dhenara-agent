from dhenara.client import Client
from dhenara.types import FlowNodeInput, UserInput
from dhenara.types.api import SSEEventType, SSEResponse


def get_api_key():
    with open(".api_key.txt") as file:
        return file.read().strip()


api_key = get_api_key()

_refnum = "22158308"  #  Streaming


def main():
    client = Client(
        api_key=api_key,
        base_url="http://localhost:8000",
    )

    user_input = UserInput(
        content="What is ephatha. Explain in less than 200 words.",  # "When bible was written",
    )
    node_input = FlowNodeInput(user_input=user_input)
    # Execute endpoint normally

    response = client.execute_endpoint(
        refnum=_refnum,
        node_input=node_input,
        stream=True,
    )

    print(f"Resposne is: {response}")

    for chunk in response:
        if type(chunk) is not SSEResponse:
            print(f"ERROR: iunknonw type {type(chunk)}")

        if chunk.event == SSEEventType.ERROR:
            print(f"Error: {chunk}")
            break

        if chunk.event == SSEEventType.TOKEN_STREAM:
            #     chat_response = StreamingChatResponse(
            #         event=parsed.event,
            #         data=parsed.data,
            #         id=parsed.id,
            #         retry=parsed.retry,
            #     )

            text = chunk.data.content
            # Process chunk data
            print(text, end="", flush=True)

            if chunk.data.done:
                break


if __name__ == "__main__":
    main()
