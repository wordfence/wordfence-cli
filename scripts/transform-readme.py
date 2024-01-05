#!/usr/bin/env python3
import re
import sys
from urllib.parse import urljoin


MARKDOWN_LINK_PATTERN = re.compile(r'\[([^]]*)\]\(([^)]*)\)')


def make_links_absolute(content: str, link_base: str) -> str:

    def make_absolute(match) -> str:
        text = match.group(1)
        link = match.group(2)
        link = urljoin(link_base, link)
        return f'[{text}]({link})'

    return MARKDOWN_LINK_PATTERN.sub(make_absolute, content)


def transform_readme(path: str, link_base: str):
    with open(path, 'r+') as file:
        content = file.read()
        content = make_links_absolute(content, link_base)
        file.seek(0)
        file.truncate()
        file.write(content)


if __name__ == '__main__':
    try:
        path = sys.argv[1]
        link_base = sys.argv[2]
        transform_readme(path, link_base)
    except KeyError:
        raise Exception(
                'A README path and link base must be provided'
            )
