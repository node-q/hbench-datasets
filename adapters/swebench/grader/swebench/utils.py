import re


def ansi_escape(text: str) -> str:
    """
    Remove ANSI codes from text
    """
    return re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])").sub("", text)
