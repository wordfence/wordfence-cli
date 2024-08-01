from ctypes import c_char_p, c_void_p, c_int, c_ulong, c_ubyte, byref, \
        Structure, POINTER, CFUNCTYPE
from enum import IntEnum
from typing import Optional

from ..library import load_library, LibraryNotAvailableException
from ..encoding import bytes_to_str

from .pcre import PcreException, PcreLibraryNotAvailableException, \
    PcreOptions, \
    PCRE_DEFAULT_OPTIONS

try:
    pcre = load_library('pcre')
except LibraryNotAvailableException:
    raise PcreLibraryNotAvailableException('Failed to load libpcre')


_pcre_version = pcre.pcre_version
_pcre_version.argtypes = []
_pcre_version.restype = c_char_p
VERSION = bytes_to_str(_pcre_version())


class PcreError(IntEnum):
    NOMATCH = -1
    NULL = -2
    BADOPTION = -3
    BADMAGIC = -4
    UNKNOWN_OPCODE = -5
    NOMEMORY = -6
    NOSUBSTRING = -7
    MATCHLIMIT = -8
    CALLOUT = -9
    BADUTF = -10
    BASEUTF_OFFSET = -11
    PARTIAL = -12
    BADPARTIAL = -13
    INTERNAL = -14
    BADCOUNT = -15
    DFA_UITEM = -16
    DFA_COND = -17
    DFA_UMLIMIT = -18
    DFA_WSSIZE = -19
    DFA_RECURSE = -20
    RECURSION_LIMIT = -21
    NULLWSLIMIT = -22
    BADNEWLINE = -23
    BADOFFSET = -24
    SHORTUTF = -25
    RECURSELOOP = -26
    JIT_STACKLIMIT = -27
    BADMODE = -28
    BADENDIANNESS = -29
    DFA_BADRESTART = -30
    JIT_BADOPTION = -31
    BADLENGTH = -32
    UNSET = -33


_pcre_config = pcre.pcre_config
_pcre_config.argtypes = [c_int, c_void_p]
_pcre_config.restype = c_int

PCRE_CONFIG_JIT = 9


def _check_jit_support() -> bool:
    value = c_int(0)
    result = _pcre_config(PCRE_CONFIG_JIT, byref(value))
    if result == 0:
        return value.value == 1
    raise PcreException(f'Checking for JIT support failed, code {result}')


HAS_JIT_SUPPORT = _check_jit_support()


class _StructPcre(Structure):
    pass


_pcre_p = POINTER(_StructPcre)
_pcre_compile = pcre.pcre_compile
_pcre_compile.argtypes = [
        c_char_p,
        c_int,
        POINTER(c_char_p),
        POINTER(c_int),
        POINTER(c_ubyte)
    ]
_pcre_compile.restype = _pcre_p


class _StructPcreExtra(Structure):
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


_pcre_extra_p = POINTER(_StructPcreExtra)
_pcre_study = pcre.pcre_study
_pcre_study.argtypes = [_pcre_p, c_int, POINTER(c_char_p)]
_pcre_study.restype = _pcre_extra_p


_pcre_free_study = pcre.pcre_free_study
_pcre_free_study.argtypes = [_pcre_extra_p]
_pcre_free_study.restype = None


_pcre_exec = pcre.pcre_exec
_pcre_exec.argtypes = [
        _pcre_p,
        _pcre_extra_p,
        c_char_p,
        c_int,
        c_int,
        c_int,
        c_void_p,
        c_int
    ]
_pcre_exec.restype = c_int


_pcre_free_address = c_void_p.in_dll(pcre, 'pcre_free').value
_pcre_free_prototype = CFUNCTYPE(None, c_void_p)
_pcre_free = _pcre_free_prototype(_pcre_free_address)


if HAS_JIT_SUPPORT:
    class _StructPcreJitStack(Structure):
        pass

    _pcre_jit_stack_p = POINTER(_StructPcreJitStack)

    _pcre_jit_stack_alloc = pcre.pcre_jit_stack_alloc
    _pcre_jit_stack_alloc.argtypes = [c_int, c_int]
    _pcre_jit_stack_alloc.restype = _pcre_jit_stack_p

    _pcre_jit_stack_free = pcre.pcre_jit_stack_free
    _pcre_jit_stack_free.argtypes = [_pcre_jit_stack_p]
    _pcre_jit_stack_free.restype = None

    _pcre_jit_exec = pcre.pcre_jit_exec
    _pcre_jit_exec.argtypes = [
            _pcre_p,
            _pcre_extra_p,
            c_char_p,
            c_int,
            c_int,
            c_int,
            c_void_p,
            c_int,
            _pcre_jit_stack_p
        ]
    _pcre_jit_exec.restype = c_int


PCRE_EXTRA_MATCH_LIMIT = 0x0012
PCRE_EXTRA_MATCH_LIMIT_RECURSION = 0x0010
PCRE_STUDY_JIT_COMPILE = 0x0001
PCRE_STUDY_EXTRA_NEEDED = 0x0008


PCRE_JIT_STACK_MIN_SIZE = 32 * 1024
PCRE_JIT_STACK_MAX_SIZE = 64 * 1024


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

    def __init__(
                self,
                pattern: str,
                options: PcreOptions = PCRE_DEFAULT_OPTIONS
            ):
        self.pattern = pattern
        self.options = options
        self._compile()

    def _compile(self) -> None:
        pattern_cstr = c_char_p(self.pattern.encode('utf8'))
        error_message = c_char_p(None)
        error_offset = c_int(-1)
        self.compiled = _pcre_compile(
                pattern_cstr,
                self.options._get_compilation_options(),
                byref(error_message),
                byref(error_offset),
                None
            )
        if not self.compiled:
            offset = error_offset.value
            message = error_message.value.decode('utf8')
            raise PcreException(
                    f'Pattern compilation failed at offset {offset}: {message}'
                )
        study_options = c_int(PCRE_STUDY_JIT_COMPILE | PCRE_STUDY_EXTRA_NEEDED)
        self.extra = _pcre_study(
                self.compiled,
                study_options,
                byref(error_message)
            )
        self.extra.flags = c_ulong(
                PCRE_EXTRA_MATCH_LIMIT | PCRE_EXTRA_MATCH_LIMIT_RECURSION
            )
        self.extra.match_limit = c_ulong(self.options.match_limit)
        self.extra.match_limit_recursion = \
            c_ulong(self.options.match_limit_recursion)

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
            try:
                error = PcreError(result)
                if error is PcreError.NOMATCH:
                    return None
                else:
                    raise PcreException(
                            'Matching failed with error: '
                            f'{error.name}({error.value})'
                        )
            except ValueError:
                raise PcreException(
                        f'Matching failed with unknown error: {result}'
                    )
        else:
            matched_string = subject[ovector[0]:ovector[1]]
            return PcreMatch(matched_string)

    def _free(self) -> None:
        if self.extra is not None and _pcre_free_study is not None:
            _pcre_free_study(self.extra)
            self.extra = None
        if self.compiled is not None and _pcre_free is not None:
            _pcre_free(self.compiled)
            self.compiled = None

    def __del__(self) -> None:
        self._free()

    def __getstate__(self) -> dict:
        return {
                'pattern': self.pattern,
                'options': self.options
            }

    def __setstate__(self, state) -> None:
        self.pattern = state['pattern']
        self.options = state['options']
        self._compile()
