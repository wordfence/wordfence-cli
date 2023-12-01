import logging
from typing import Optional
from enum import IntEnum
from dataclasses import dataclass

from .formatting import ConfigurableFormatter

DEFAULT_LOGGER_NAME = 'wordfence'
VERBOSE = 15


class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    VERBOSE = VERBOSE
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


logging.addLevelName(LogLevel.VERBOSE.value, LogLevel.VERBOSE.name)

logging.basicConfig(format='%(message)s')
log = logging.getLogger(DEFAULT_LOGGER_NAME)
root_log = logging.getLogger()

initial_handler: Optional[logging.Handler] = None


def remove_initial_handler() -> None:
    global initial_handler
    if initial_handler is not None:
        return
    initial_handler = root_log.handlers[0]
    root_log.removeHandler(initial_handler)


def restore_initial_handler(error_if_not_set: bool = False) -> None:
    global initial_handler
    if initial_handler is None:
        if error_if_not_set:
            raise ValueError("Unknown initial handler")
        return
    root_log.addHandler(initial_handler)
    initial_handler = None


def set_log_format(colored: bool = False, prefixed: bool = False) -> None:
    for handler in root_log.handlers:
        handler.setFormatter(
                ConfigurableFormatter(colored, prefixed)
            )


@dataclass
class LogSettings:
    level: LogLevel = LogLevel.WARNING
    colored: bool = False
    prefixed: bool = False

    def apply(self) -> None:
        log.setLevel(self.level)
        set_log_format(
                colored=self.colored,
                prefixed=self.prefixed
            )
