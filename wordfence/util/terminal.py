import sys
from enum import IntEnum


def supports_colors() -> bool:
    # TODO: Implement more detailed checks for color support
    return sys.stdout is not None and sys.stdout.isatty()


class Color(IntEnum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    RESET = 0


ESC = '\x1b'


def escape(color: Color, bold: bool = False) -> str:
    fields = []
    if bold:
        fields.append('1')
    else:
        fields.append('22')
    fields.append(str(color.value))
    sequence = ';'.join(fields)
    return f'{ESC}[{sequence}m'


RESET = escape(color=Color.RESET)
