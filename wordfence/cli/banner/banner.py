import os
import sys

FULL_BANNER_FILENAME = 'full_banner.txt'
TEXT_BANNER_FILENAME = 'text_banner.txt'
FULL_BANNER_MIN_TERMINAL_WIDTH = 82


def show_welcome_banner():
    if os.get_terminal_size().columns >= FULL_BANNER_MIN_TERMINAL_WIDTH:
        file = FULL_BANNER_FILENAME
    else:
        file = TEXT_BANNER_FILENAME

    with open(os.path.dirname(__file__) + '/' + file, 'r') as stream:
        print(stream.read())
        stream.close()


def should_show_welcome_banner(banner_enabled):
    return banner_enabled and sys.stdout.isatty()


def show_welcome_banner_if_enabled(config) -> None:
    if should_show_welcome_banner(config.banner):
        show_welcome_banner()
