import sys
from enum import IntEnum


def supports_colors() -> bool:
    # TODO: Implement more detailed checks for color support
    return sys.stdout.isatty()


class Color(IntEnum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37


ESC = '\x1b'


def escape(color: Color) -> str:
    return f'{ESC}[{color.value}m'
