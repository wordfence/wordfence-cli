from ctypes import cdll, c_char_p, c_void_p, c_int, c_ulong, c_ubyte, byref, \
        create_string_buffer, Structure, POINTER
from typing import Optional

pcre = cdll.LoadLibrary('libpcre.so')


_pcre_version = pcre.pcre_version
_pcre_version.restype = c_char_p
VERSION = _pcre_version()


PCRE_ERROR_NOMATCH = -1
PCRE_ERROR_BADOPTION = 3


_pcre_config = pcre.pcre_config
_pcre_config.restype = c_int

PCRE_CONFIG_JIT = 9


def _check_jit_support() -> bool:
    value = c_int(0)
    result = _pcre_config(PCRE_CONFIG_JIT, byref(value))
    if result == 0:
        return value.value == 1
    raise PcreException(f'Checking for JIT support failed, code {result}')


HAS_JIT_SUPPORT = _check_jit_support()

_pcre_compile = pcre.pcre_compile
_pcre_compile.restype = c_void_p

if HAS_JIT_SUPPORT:
    _pcre_jit_stack_alloc = pcre.pcre_jit_stack_alloc
    _pcre_jit_stack_alloc.restype = c_void_p
    _pcre_jit_stack_free = pcre.pcre_jit_stack_free


_pcre_exec = pcre.pcre_exec
_pcre_exec.restype = c_int


_pcre_jit_exec = pcre.pcre_jit_exec
_pcre_jit_exec.restype = c_int


PCRE_EXTRA_MATCH_LIMIT = 0x0012
PCRE_EXTRA_MATCH_LIMIT_RECURSION = 0x0010
PCRE_STUDY_JIT_COMPILE = 0x0001
PCRE_STUDY_EXTRA_NEEDED = 0x0008
PCRE_CASELESS = 0x00000001


PCRE_JIT_STACK_MIN_SIZE = 32 * 1024
PCRE_JIT_STACK_MAX_SIZE = 64 * 1024


class PcreException(Exception):
    pass


class PcreExtra(Structure):
    _fields_ = [
                ('flags', c_ulong),
                ('study_data', c_void_p),
                ('match_limit', c_ulong),
                ('callout_data', c_void_p),
                ('tables', POINTER(c_ubyte)),
                ('match_limit_recursion', c_ulong),
                ('mark', POINTER(c_char_p)),
                ('executable_jit', c_void_p)
            ]


_pcre_study = pcre.pcre_study
_pcre_study.restype = POINTER(PcreExtra)


_pcre_free_study = pcre.pcre_free_study


class PcreJitStack:

    def __init__(
                self,
                min_size: int = PCRE_JIT_STACK_MIN_SIZE,
                max_size: int = PCRE_JIT_STACK_MAX_SIZE
            ):
        self.min_size = min_size
        self.max_size = max_size
        self._jit_stack = None

    def allocate(self) -> None:
        if HAS_JIT_SUPPORT:
            self._jit_stack = _pcre_jit_stack_alloc(
                    self.min_size,
                    self.max_size
                )

    def _allocate_if_necessary(self) -> None:
        if self._jit_stack is None:
            self.allocate()

    def free(self) -> None:
        if HAS_JIT_SUPPORT and self._jit_stack is not None:
            _pcre_jit_stack_free(self._jit_stack)

    def __enter__(self):
        self._allocate_if_necessary()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.free()

    def _get_jit_stack(self):
        self._allocate_if_necessary()
        return self._jit_stack


class PcreMatch:

    def __init__(self, matched_string: bytes):
        self.matched_string = matched_string


class PcrePattern:

    def __init__(self, pattern: str):
        self._compile(pattern)

    def _compile(self, pattern: str) -> c_void_p:
        pattern_cstr = c_char_p(pattern.encode('utf8'))
        error_buffer = create_string_buffer(100)
        error_offset = c_int(-1)
        options = c_int(PCRE_CASELESS)
        self.compiled = _pcre_compile(
                pattern_cstr,
                options,
                byref(error_buffer),
                byref(error_offset),
                None
            )
        if not self.compiled:
            offset = error_offset.value
            message = error_buffer.value
            raise PcreException(
                    f'Pattern compilation failed at offset {offset}: {message}'
                )
        study_options = c_int(PCRE_STUDY_JIT_COMPILE | PCRE_STUDY_EXTRA_NEEDED)
        self.extra = _pcre_study(
                self.compiled,
                study_options,
                byref(error_buffer)
            )
        self.extra.flags = c_ulong(
                PCRE_EXTRA_MATCH_LIMIT | PCRE_EXTRA_MATCH_LIMIT_RECURSION
            )
        self.extra.match_limit = c_ulong(100000)
        self.extra.match_limit_recursion = c_ulong(100000)

    def match(
                self,
                subject: bytes,
                jit_stack: PcreJitStack = None
            ) -> Optional[PcreMatch]:
        if jit_stack is None and HAS_JIT_SUPPORT:
            jit_stack = PcreJitStack()
            temporary_jit_stack = True
        else:
            temporary_jit_stack = False
        subject_cstr = c_char_p(subject)
        subject_length = c_int(len(subject))
        start_offset = c_int(0)
        options = c_int(0)
        ovector = c_int * 3
        ovector = ovector(0, 0, 0)
        ovecsize = c_int(3)
        if HAS_JIT_SUPPORT:
            result = _pcre_jit_exec(
                    self.compiled,
                    self.extra,
                    subject_cstr,
                    subject_length,
                    start_offset,
                    options,
                    byref(ovector),
                    ovecsize,
                    jit_stack._get_jit_stack()
                )
        else:
            result = _pcre_exec(
                    self.compiled,
                    self.extra,
                    subject_cstr,
                    subject_length,
                    start_offset,
                    options,
                    byref(ovector),
                    ovecsize,
                )
        if temporary_jit_stack:
            jit_stack.free()
        if result < 0:
            if result == PCRE_ERROR_NOMATCH:
                return None
            else:
                raise PcreException(
                        f'Matching failed with error code: {result}'
                    )
        else:
            matched_string = subject[ovector[0]:ovector[1]]
            return PcreMatch(matched_string)

    def _free(self) -> None:
        _pcre_free_study(self.extra)
