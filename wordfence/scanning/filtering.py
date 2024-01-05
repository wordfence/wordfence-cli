import re
import os
from typing import Optional, List, Callable, Pattern, AnyStr


class FilterCondition:

    def __init__(self, test: Callable[[str], bool], allow: bool = True):
        self.test = test
        self.allow = allow

    def evaluate(self, path: str) -> bool:
        return self.test(path)


class FileFilter:

    def __init__(self, conditions: Optional[List[FilterCondition]] = None):
        self._conditions = conditions if conditions is not None else []

    def add_condition(self, condition: FilterCondition) -> None:
        self._conditions.append(condition)

    def add(self, test: Callable[[str], bool], allow: bool = True):
        self.add_condition(FilterCondition(test, allow))

    def filter(self, path: str) -> bool:
        allowed = False
        for condition in self._conditions:
            if condition.allow and allowed:
                continue  # Only a single allow condition needs to match
            matched = condition.evaluate(path)
            if matched:
                if condition.allow:
                    allowed = True
                else:
                    return False  # Any disallowed condition takes precedence
        return allowed


def matches_regex(regex: re.Pattern, string: str) -> bool:
    return regex.search(string) is not None


def filter_any(path: str) -> bool:
    return True


PATTERN_PHP = re.compile(
        r'\.(?:php(?:\d+)?|phtml)(\.|$)',
        re.IGNORECASE
    )
PATTERN_HTML = re.compile(
        r'\.(?:html?)(\.|$)',
        re.IGNORECASE
    )
PATTERN_JS = re.compile(
        r'\.(?:js|svg)(\.|$)',
        re.IGNORECASE
    )
PATTERN_IMAGES = re.compile(
        (
            r'\.(?:jpg|jpeg|mp3|avi|m4v|mov|mp4|gif|png|tiff?|svg|sql|js|tbz2?'
            r'|bz2?|xz|zip|tgz|gz|tar|log|err\d+)(\.|$)'
        ),
        re.IGNORECASE
    )


def filter_php(path: str) -> bool:
    return matches_regex(PATTERN_PHP, path)


def filter_html(path: str) -> bool:
    return matches_regex(PATTERN_HTML, path)


def filter_js(path: str) -> bool:
    return matches_regex(PATTERN_JS, path)


def filter_images(path: str) -> bool:
    return matches_regex(PATTERN_IMAGES, path)


class FilenameFilter:

    def __init__(self, value: str):
        self.value = value

    def __call__(self, path: str):
        filename = os.path.basename(path)
        return filename == self.value


class Filter:

    def __init__(self, pattern: Pattern[AnyStr]):
        self.pattern = pattern

    def __call__(self, path: str) -> bool:
        return matches_regex(self.pattern, path)


class InvalidPatternException(Exception):

    def __init__(self, pattern: str):
        self.pattern = pattern


def filter_pattern(regex: str) -> Callable[[str], bool]:
    try:
        pattern = re.compile(regex)
        return Filter(pattern)
    except re.error:
        raise InvalidPatternException(regex)
