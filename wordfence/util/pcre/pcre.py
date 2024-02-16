from ctypes import c_int

from ..library import LibraryNotAvailableException


class PcreException(Exception):
    pass


class PcreLibraryNotAvailableException(
            PcreException,
            LibraryNotAvailableException
        ):
    pass


PCRE_CASELESS = 0x00000001
PCRE_DEFAULT_MATCH_LIMIT = 1000000
PCRE_DEFAULT_MATCH_LIMIT_RECURSION = 100000


class PcreOptions:

    def __init__(
                self,
                caseless: bool = False,
                match_limit: int = PCRE_DEFAULT_MATCH_LIMIT,
                match_limit_recursion: int = PCRE_DEFAULT_MATCH_LIMIT_RECURSION
            ):
        self.caseless = caseless
        self.match_limit = match_limit
        self.match_limit_recursion = match_limit_recursion
        self._compilation_options = None

    def _get_compilation_options(self) -> c_int:
        if self._compilation_options is None:
            options = 0
            if self.caseless:
                options |= PCRE_CASELESS
            self._compilation_options = c_int(options)
        return self._compilation_options


PCRE_DEFAULT_OPTIONS = PcreOptions()


try:
    from .bindings import *  # noqa: F401, F403
    AVAILABLE = True
except PcreLibraryNotAvailableException:
    AVAILABLE = False
