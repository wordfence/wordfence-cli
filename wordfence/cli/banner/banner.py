import os
import sys

TEXT_BANNER = r"""
 _       __               __  ____
| |     / /___  _________/ / / __/__  ____  ________
| | /| / / __ \/ ___/ __  /_/ /_/ _ \/ __ \/ ___/ _ \
| |/ |/ / /_/ / /  / /_/ /_  __/  __/ / / / /__/  __/
|__/|__/\____/_/   \____/ /_/  \___/_/ /_/\___/\___/
                                      ____ _     ___
                                     / ___| |   |_ _|
                                    | |   | |    | |
                                    | |___| |___ | |
                                     \____|_____|___|
"""

LOGO = r"""
             ▓▓▓
        ▓▓▓▓▓   ▓▓▓▓▓
  ▓▓▓▓▓▓▓           ▓▓▓▓▓▓▓
 ▓▓           ▓           ▓▓
▓▓     ▓▓    ▓▓▓    ▓▓     ▓▓
▓▓      ▓     ▓     ▓      ▓▓
▓▓    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓    ▓▓
▓▓  ▓▓▓ ▓    ▓▓▓    ▓ ▓▓▓  ▓▓
▓▓▓▓▓   ▓    ▓▓▓    ▓   ▓▓▓▓▓
 ▓▓     ▓   ▓▓ ▓▓   ▓     ▓▓
  ▓▓▓▓▓▓▓▓▓▓▓▓ ▓▓▓▓▓▓▓▓▓▓▓▓
"""


class Banner:

    def __init__(self, content: str):
        self.content = content
        self.process_content()

    def process_content(self) -> None:
        self.row_count = 0
        self.column_count = 0
        rows = self.content.split('\n')
        for row in rows:
            self.column_count = max(self.column_count, len(row.rstrip()))
            self.row_count += 1
        for index, row in enumerate(rows):
            rows[index] = row.ljust(self.column_count)
        self.rows = rows

    def merge(self, banner, separator: str = ' ') -> None:
        height_difference = self.row_count - banner.row_count
        self_taller = height_difference > 0
        taller = self if self_taller else banner
        if self_taller:
            self_offset = 0
            banner_offset = -height_difference
        else:
            self_offset = -height_difference
            banner_offset = 0
        height_difference = abs(height_difference)
        new_rows = []
        for index in range(0, height_difference):
            new_rows.append(taller.rows[index])
        for index in range(height_difference, taller.row_count):
            new_rows.append(
                    self.rows[index + self_offset] +
                    separator +
                    banner.rows[index + banner_offset]
                )
        self.rows = new_rows
        self.row_count += height_difference
        self.column_count += len(separator) + banner.column_count

    def display(self) -> None:
        for row in self.rows:
            print(row)

    def __str__(self) -> str:
        return self.content


def add_logo(banner) -> str:
    pass


def get_welcome_banner():
    terminal_columns = os.get_terminal_size().columns
    text = Banner(TEXT_BANNER)
    logo = Banner(LOGO)
    combined = Banner(LOGO)
    combined.merge(text)
    variants = [
            combined,
            text,
            logo
        ]
    for banner in variants:
        if banner.column_count <= terminal_columns:
            return banner
    return None


def show_welcome_banner():
    banner = get_welcome_banner()
    if banner is not None:
        banner.display()


def should_show_welcome_banner(banner_enabled):
    return banner_enabled \
            and sys.stdout.isatty() \
            and sys.stdout.encoding == 'utf-8'


def show_welcome_banner_if_enabled(config) -> None:
    if should_show_welcome_banner(config.banner) and \
            not config.get('quiet, False') and \
            not config.get('progress', False):
        show_welcome_banner()
