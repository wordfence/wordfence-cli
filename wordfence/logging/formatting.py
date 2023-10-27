import logging

from ..util.terminal import Color, escape, RESET


class ColoredFormatter(logging.Formatter):

    def get_style(self, level) -> str:
        if level >= logging.ERROR:
            return escape(color=Color.RED)
        if level >= logging.WARNING:
            return escape(color=Color.YELLOW)
        if level <= logging.DEBUG:
            return escape(color=Color.WHITE)
        return escape(color=Color.GREEN)

    def format(self, record) -> str:
        style = self.get_style(record.levelno)
        message = super().format(record)
        return f'{style}{message}{RESET}'
