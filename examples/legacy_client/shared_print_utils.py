# shared_print_utils.py
from dhenara.ai.types import ChatResponseContentItemType


class ResponseDisplayMixin:
    COLORS = {"reset": "\033[0m", "gray": "\033[90m", "yellow": "\033[93m", "blue": "\033[94m", "red": "\033[91m"}

    def print_content(self, text: str, content_type: ChatResponseContentItemType, end: str = "", flush: bool = True):
        """Unified content printing for both streaming and non-streaming responses"""
        COLORS = ResponseDisplayMixin.COLORS  # noqa: N806

        if content_type == ChatResponseContentItemType.REASONING:
            print(f"{COLORS['gray']}{text}{COLORS['reset']}", end=end, flush=flush)
        elif content_type == ChatResponseContentItemType.TOOL_CALL:
            print(f"{COLORS['yellow']}{text}{COLORS['reset']}", end=end, flush=flush)
        elif content_type == ChatResponseContentItemType.GENERIC:
            print(f"{COLORS['blue']}{text}{COLORS['reset']}", end=end, flush=flush)
        else:  # Default TEXT type
            print(text, end=end, flush=flush)

    def print_content_type_header(self, content_type: ChatResponseContentItemType):
        COLORS = ResponseDisplayMixin.COLORS  # noqa: N806
        if content_type == ChatResponseContentItemType.TEXT:
            print(f"\n[Text:]")  # noqa: F541
        elif content_type == ChatResponseContentItemType.REASONING:
            print(f"\n{COLORS['gray']}[Reasoning:]{COLORS['reset']}")
        elif content_type == ChatResponseContentItemType.TOOL_CALL:
            print(f"\n{COLORS['yellow']}[Tool Call:]{COLORS['reset']}")
        elif content_type == ChatResponseContentItemType.GENERIC:
            print(f"\n{COLORS['blue']}[Generic:]{COLORS['reset']}")
        else:
            pass

    def print_warning(self, message: str):
        """Unified error printing"""
        COLORS = ResponseDisplayMixin.COLORS  # noqa: N806
        print(f"\n\n{COLORS['yellow']}WARNING: {message}{COLORS['reset']}")

    def print_error(self, message: str):
        """Unified error printing"""
        COLORS = ResponseDisplayMixin.COLORS  # noqa: N806
        print(f"\n{COLORS['red']}Error: {message}{COLORS['reset']}")
