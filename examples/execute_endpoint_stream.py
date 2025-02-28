from dhenara.agent.client import Client
from dhenara.agent.types import FlowNodeInput, UserInput
from dhenara.agent.types.flow import Resource, ResourceObjectTypeEnum, ResourceQueryFieldsEnum
from dhenara.ai.types import ChatResponseChunk
from dhenara.ai.types.shared.api import SSEErrorResponse, SSEEventType, SSEResponse
from shared_print_utils import ResponseDisplayMixin


def get_api_key():
    with open(".api_key.txt") as file:
        return file.read().strip()


api_key = get_api_key()

_refnum = "22143274"  #  Streaming


def main():
    client = Client(
        api_key=api_key,
        base_url="http://localhost:8000",
    )

    user_input = UserInput(
        content="What is ephatha. Explain in less than 200 words.",  # "When bible was written",
        # content="Count 1 to 10 in words.",  # "When bible was written",
    )
    node_input = FlowNodeInput(
        user_input=user_input,
        resources=[
            Resource(
                object_type=ResourceObjectTypeEnum.ai_model_endpoint,
                object_id=None,
                query={ResourceQueryFieldsEnum.model_name: "gemini-2.0-flash-lite"},
                # query={ResourceQueryFieldsEnum.model_name: "gemini-1.5-pro"},
                # query={ResourceQueryFieldsEnum.model_name: "claude-3-5-haiku"},
                # query={ResourceQueryFieldsEnum.model_name: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"},
                # query={ResourceQueryFieldsEnum.model_name: "gpt-4o-mini"},
                # query={ResourceQueryFieldsEnum.model_name: "o3-mini"},
                # query={ResourceQueryFieldsEnum.model_name: "DeepSeek-R1"},
                # query={ResourceQueryFieldsEnum.model_name: "claude-3-7-sonnet"},
            ),
        ],
    )

    response = client.execute_endpoint(
        refnum=_refnum,
        node_input=node_input,
        stream=True,
        response_model=ChatResponseChunk,
    )

    stream_procesor = StreamProcesor()
    stream_procesor.process_stream_response(response)


class StreamProcesor(ResponseDisplayMixin):
    def __init__(self):
        super().__init__()
        self.previous_content_delta = None

    def process_stream_response(self, response):
        print("\nAssistant: ", end="", flush=True)

        try:
            for chunk in response:
                if isinstance(chunk, SSEErrorResponse):
                    self.print_error(f"{chunk.data.error_code}: {chunk.data.message}")
                    break

                if not isinstance(chunk, SSEResponse):
                    self.print_error(f"Unknown type {type(chunk)}")
                    continue

                if chunk.event == SSEEventType.ERROR:
                    self.print_error(f"Stream Error: {chunk}")
                    break

                if chunk.event == SSEEventType.TOKEN_STREAM:
                    self.print_stream_chunk(chunk.data)
                    if chunk.data.done:
                        break

        except KeyboardInterrupt:
            self.print_warning("Stream interrupted by user")
        except Exception as e:
            self.print_error(f"Error processing stream: {e!s}")
        finally:
            print("\n")

    # For streaming responses
    def print_stream_chunk(self, chunk: ChatResponseChunk):
        """Print the content from a stream chunk"""
        for choice_delta in chunk.choice_deltas:
            if not choice_delta.content_deltas:
                continue

            for content_delta in choice_delta.content_deltas:
                same_content = self.previous_content_delta and self.previous_content_delta.index == content_delta.index and self.previous_content_delta.type == content_delta.type
                if not same_content:
                    self.previous_content_delta = content_delta
                    self.print_content_type_header(content_delta.type)

                text = content_delta.get_text_delta()
                if text:
                    self.print_content(text, content_delta.type, end="", flush=True)


if __name__ == "__main__":
    main()
