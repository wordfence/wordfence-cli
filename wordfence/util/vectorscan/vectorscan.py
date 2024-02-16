from ..library import LibraryNotAvailableException


class VectorscanException(Exception):
    pass


class VectorscanLibraryNotAvailableException(
            VectorscanException,
            LibraryNotAvailableException
        ):
    pass


try:
    from .bindings import *  # noqa: F401, F403
    AVAILABLE = True
except VectorscanLibraryNotAvailableException:
    AVAILABLE = False
