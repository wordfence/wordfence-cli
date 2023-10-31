import logging
from typing import Optional

from .formatting import ColoredFormatter

DEFAULT_LOGGER_NAME = 'wordfence'
VERBOSE = 15

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


def enable_log_colors() -> None:
    root_log.handlers[0].setFormatter(ColoredFormatter())
