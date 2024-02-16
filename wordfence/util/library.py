from ctypes import cdll, CDLL
from ctypes.util import find_library
from importlib import import_module


class LibraryNotAvailableException(Exception):
    pass


def load_library(name: str) -> CDLL:
    pathname = find_library(name)
    if pathname is None:
        raise LibraryNotAvailableException()
    try:
        library = cdll.LoadLibrary(pathname)
        return library
    except OSError:
        raise LibraryNotAvailableException


class OptionalUtility:

    def __init__(self, name):
        try:
            self.module = import_module('.' + name, 'wordfence.util')
        except LibraryNotAvailableException:
            self.module = None

    def is_available(self) -> bool:
        return self.module is not None
