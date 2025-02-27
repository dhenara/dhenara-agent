# shared_print_utils.py
from dhenara.ai.types import ChatResponseContentItemType

COLORS = {"reset": "\033[0m", "gray": "\033[90m", "yellow": "\033[93m", "blue": "\033[94m", "red": "\033[91m"}


def print_content(text: str, content_type: ChatResponseContentItemType, end: str = "", flush: bool = True):
    """Unified content printing for both streaming and non-streaming responses"""
    if content_type == ChatResponseContentItemType.REASONING:
        print(f"{COLORS['gray']}[Reasoning: {text}]{COLORS['reset']}", end=end, flush=flush)
    elif content_type == ChatResponseContentItemType.TOOL_CALL:
        print(f"\n{COLORS['yellow']}[Tool Call: {text}]{COLORS['reset']}", end=end, flush=flush)
    elif content_type == ChatResponseContentItemType.GENERIC:
        print(f"\n{COLORS['blue']}[Generic: {text}]{COLORS['reset']}", end=end, flush=flush)
    else:  # Default TEXT type
        print(text, end=end, flush=flush)


def print_warning(message: str):
    """Unified error printing"""
    print(f"\n\n{COLORS['yellow']}WARNING: {message}{COLORS['reset']}")


def print_error(message: str):
    """Unified error printing"""
    print(f"\n{COLORS['red']}Error: {message}{COLORS['reset']}")
