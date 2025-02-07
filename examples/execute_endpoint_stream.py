from dhenara.client import Client
from dhenara.types import FlowNodeInput, UserInput


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
        print(chunk)


if __name__ == "__main__":
    main()
