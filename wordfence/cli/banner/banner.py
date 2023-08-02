import os

FULL_BANNER_FILENAME = 'full_banner.txt'
TEXT_BANNER_FILENAME = 'text_banner.txt'
FULL_BANNER_MIN_TERMINAL_WIDTH = 82


def welcome_banner():
    if os.get_terminal_size().columns >= FULL_BANNER_MIN_TERMINAL_WIDTH:
        file = FULL_BANNER_FILENAME
    else:
        file = TEXT_BANNER_FILENAME

    with open(os.path.dirname(__file__) + '/' + file, 'r') as stream:
        print(stream.read())
        stream.close()
