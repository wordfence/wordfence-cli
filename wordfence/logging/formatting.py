import logging

from ..util.terminal import Color, escape, RESET


class ConfigurableFormatter(logging.Formatter):

    def __init__(self, colored: bool = False, prefixed: bool = False):
        super().__init__()
        self.colored = colored
        self.prefixed = prefixed
        self.reset = RESET if colored else ''

    def get_style(self, level) -> str:
        if not self.colored:
            return ''
        if level >= logging.ERROR:
            return escape(color=Color.RED)
        if level >= logging.WARNING:
            return escape(color=Color.YELLOW)
        if level <= logging.DEBUG:
            return escape(color=Color.WHITE)
        return escape(color=Color.GREEN)

    def get_prefix(self, level) -> str:
        if not self.prefixed or not level:
            return ''
        return f'{level}: '

    def format(self, record) -> str:
        style = self.get_style(record.levelno)
        prefix = self.get_prefix(record.levelname)
        message = super().format(record)
        return f'{style}{prefix}{message}{self.reset}'
