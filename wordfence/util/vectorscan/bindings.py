from ctypes import Structure, POINTER, c_char_p, c_int, \
    c_void_p, c_uint, c_ulonglong, c_size_t, byref, string_at, CFUNCTYPE
from enum import IntFlag, IntEnum
from typing import Dict, Optional, Callable, Union, Any

from ..library import load_library, LibraryNotAvailableException
from ..encoding import bytes_to_str
from .. import signals

from .vectorscan import VectorscanException, \
    VectorscanLibraryNotAvailableException


try:
    hs = load_library('hs')
except LibraryNotAvailableException:
    raise VectorscanLibraryNotAvailableException('Failed to load libhs')


_hs_version = hs.hs_version
_hs_version.argtypes = []
_hs_version.restype = c_char_p
VERSION = bytes_to_str(_hs_version())
API_VERSION = ''.join(VERSION.split()[:1])


class _StructHsDatabase(Structure):
    pass


_hs_database_p = POINTER(_StructHsDatabase)


_hs_error = c_int


class _StructHsCompileError(Structure):
    _fields_ = [
            ('message', c_char_p),
            ('expression', c_int)
        ]


_hs_compile_error_p = POINTER(_StructHsCompileError)


class _StructHsPlatformInfo(Structure):
    _fields_ = [
            ('tune', c_uint),
            ('cpu_features', c_ulonglong),
            ('reserved1', c_ulonglong),
            ('reserved2', c_ulonglong)
        ]


_hs_platform_info_p = POINTER(_StructHsPlatformInfo)


_hs_compile_multi = hs.hs_compile_multi
_hs_compile_multi.argtypes = [
        POINTER(c_char_p),
        POINTER(c_uint),
        POINTER(c_uint),
        c_uint,
        c_uint,
        _hs_platform_info_p,
        POINTER(_hs_database_p),
        POINTER(_hs_compile_error_p)
    ]
_hs_compile_multi.restype = _hs_error


_hs_free_database = hs.hs_free_database
_hs_free_database.argtypes = [_hs_database_p]
_hs_free_database.restype = None


_hs_serialize_database = hs.hs_serialize_database
_hs_serialize_database.argtypes = [
        _hs_database_p,
        POINTER(c_char_p),
        POINTER(c_size_t)
    ]
_hs_serialize_database.restype = _hs_error


_hs_deserialize_database = hs.hs_deserialize_database
_hs_deserialize_database.argtypes = [
        c_char_p,
        c_size_t,
        POINTER(_hs_database_p)
    ]


class _StructHsScratch(Structure):
    pass


_hs_scratch_p = POINTER(_StructHsScratch)


_hs_alloc_scratch = hs.hs_alloc_scratch
_hs_alloc_scratch.argtypes = [_hs_database_p, POINTER(_hs_scratch_p)]
_hs_alloc_scratch.restype = _hs_error


_hs_free_scratch = hs.hs_free_scratch
_hs_free_scratch.argtypes = [_hs_scratch_p]
_hs_free_scratch.restype = None


_match_event_handler = CFUNCTYPE(
        c_int,
        c_uint,
        c_ulonglong,
        c_ulonglong,
        c_uint,
        c_void_p
    )


_hs_scan = hs.hs_scan
_hs_scan.argtypes = [
        _hs_database_p,
        c_char_p,
        c_uint,
        c_uint,
        _hs_scratch_p,
        _match_event_handler,
        c_void_p
    ]
_hs_scan.restype = _hs_error


class _StructHsStream(Structure):
    pass


_hs_stream_p = POINTER(_StructHsStream)


_hs_open_stream = hs.hs_open_stream
_hs_open_stream.argtypes = [
        _hs_database_p,
        c_uint,
        POINTER(_hs_stream_p)
    ]
_hs_open_stream.restype = _hs_error


_hs_scan_stream = hs.hs_scan_stream
_hs_scan_stream.argtypes = [
        _hs_stream_p,
        c_char_p,
        c_uint,
        c_uint,
        _hs_scratch_p,
        _match_event_handler,
        c_void_p
    ]
_hs_scan_stream.restype = _hs_error


_hs_reset_stream = hs.hs_reset_stream
_hs_reset_stream.argtypes = [
        _hs_stream_p,
        c_uint,
        _hs_scratch_p,
        _match_event_handler,
        c_void_p
    ]
_hs_reset_stream.restype = _hs_error


_hs_close_stream = hs.hs_close_stream
_hs_close_stream.argtypes = [
        _hs_stream_p,
        _hs_scratch_p,
        _match_event_handler,
        c_void_p
    ]
_hs_close_stream.restype = _hs_error


class VectorscanFlags(IntFlag):
    NONE = 0
    CASELESS = 1
    DOTALL = 2
    MULTILINE = 4
    SINGLEMATCH = 8
    ALLOWEMPTY = 16
    UTF8 = 32
    UCP = 64
    PREFILTER = 128
    LEFTMODE = 256
    COMBINATION = 512
    QUIET = 1024


class VectorscanMode(IntEnum):
    BLOCK = 1
    STREAM = 2
    VECTORED = 4


class VectorscanErrorType(IntEnum):
    SUCCESS = 0
    INVALID = -1
    NOMEM = -2
    SCAN_TERMINATED = -3
    COMPILER_ERROR = -4
    DB_VERSION_ERROR = -5
    DB_PLATFORM_ERROR = -6
    DB_MODE_ERROR = -7
    BAD_ALIGN = -8
    BAD_ALLOC = -9
    SCRATCH_IN_USE = -10
    ARCH_ERROR = -11
    INSUFFICIENT_SPACE = -12
    UNKNOWN_ERROR = -13


class VectorscanError(VectorscanException):

    def __init__(self, error: VectorscanErrorType):  # noqa: B042
        self.error = error


class VectorscanScanTerminated(VectorscanError):

    def __init__(self):
        super().__init__(VectorscanErrorType.SCAN_TERMINATED)


class VectorscanDatabaseIncompatible(VectorscanError):
    pass


DATABASE_COMPATIBILITY_ERRORS = [
        VectorscanErrorType.DB_VERSION_ERROR,
        VectorscanErrorType.DB_PLATFORM_ERROR,
        VectorscanErrorType.DB_MODE_ERROR
    ]


def _assert_success(error: Union[int, _hs_error]):
    try:
        if isinstance(error, _hs_error):
            error = _hs_error.value
        error = VectorscanErrorType(error)
    except ValueError:
        error = VectorscanErrorType.UNKNOWN_ERROR
    if error is not VectorscanErrorType.SUCCESS:
        if error is VectorscanErrorType.SCAN_TERMINATED:
            raise VectorscanScanTerminated()
        if error in DATABASE_COMPATIBILITY_ERRORS:
            raise VectorscanDatabaseIncompatible(error)
        raise VectorscanError(error)


class VectorscanCompilerError(VectorscanError):

    def __init__(self, message):
        super().__init__(VectorscanErrorType.COMPILER_ERROR)


def _assert_compilation_success(
            error: Union[int, _hs_error],
            compiler_error: _hs_compile_error_p
        ):
    try:
        _assert_success(error)
    except VectorscanError as e:
        if e.error is VectorscanErrorType.COMPILER_ERROR:
            raise VectorscanCompilerError(
                    compiler_error.contents.message.decode('utf-8')
                )
        else:
            raise


class VectorscanDatabase:

    def __init__(self, database: _hs_database_p):
        self._database = database

    def __del__(self) -> None:
        if self._database is not None:
            _hs_free_database(self._database)
            self._database = None

    def serialize(self) -> bytes:
        data = c_char_p()
        length = c_size_t()
        error = _hs_serialize_database(
                self._database,
                byref(data),
                byref(length)
            )
        _assert_success(error)
        return string_at(data, length.value)


class VectorscanScratch:

    def __init__(self, database: VectorscanDatabase):
        self._scratch = _hs_scratch_p()
        _hs_alloc_scratch(database._database, byref(self._scratch))

    def __del__(self) -> None:
        if self._scratch is not None:
            _hs_free_scratch(self._scratch)
            self._scratch = None


class VectorscanMatch:

    def __init__(
                self,
                identifier: int,
                start: int,
                end: int,
                context
            ):
        self.identifier = identifier
        self.start = start
        self.end = end
        self.context = context


VectorscanMatchCallback = Callable[[VectorscanMatch], bool]


def _default_match_callback(match: VectorscanMatch) -> bool:
    return False


def _wrap_match_callback(callback: VectorscanMatchCallback, context: Any):
    def wrapped_callback(
                identifier: int,
                start: int,
                end: int,
                _flags: int,
                c_context
            ) -> int:
        match = VectorscanMatch(
                identifier,
                start,
                end,
                context
            )
        should_terminate = callback(match)
        return 1 if should_terminate else 0
    return wrapped_callback


class VectorscanScanner:

    def __init__(
                self,
                database: VectorscanDatabase,
                scratch: Optional[VectorscanScratch] = None
            ):
        self.database = database
        self.scratch = scratch if scratch is not None \
            else VectorscanScratch(database)

    def _encode_data(self, data: Union[bytes, str]) -> bytes:
        if isinstance(data, str):
            data = data.encode('utf-8')
        return data


class VectorscanBlockScanner(VectorscanScanner):

    def __init__(
                self,
                database: VectorscanDatabase,
                scratch: Optional[VectorscanScratch] = None
            ):
        super().__init__(database, scratch)

    def scan(
                self,
                data: Union[bytes, str],
                callback: VectorscanMatchCallback,
                context: Optional[Any] = None
            ):
        data = self._encode_data(data)

        callback = _wrap_match_callback(callback, context)

        error = _hs_scan(
                self.database._database,
                c_char_p(data),
                c_uint(len(data)),
                c_uint(0),
                self.scratch._scratch,
                _match_event_handler(callback),
                c_void_p()
            )
        _assert_success(error)


class VectorscanStreamScanner(VectorscanScanner):

    def __init__(
                self,
                database: VectorscanDatabase,
                callback: VectorscanMatchCallback = _default_match_callback,
                context: Optional[Any] = None,
                scratch: Optional[VectorscanScratch] = None
            ):
        super().__init__(database, scratch)
        self._stream = None
        self.set_callback(callback, context)
        self._open_stream()

    def set_callback(
                self,
                callback: VectorscanMatchCallback,
                context: Optional[Any] = None
            ) -> None:
        self._callback = _match_event_handler(
                _wrap_match_callback(callback, context)
            )

    def _open_stream(self) -> None:
        stream = _hs_stream_p()
        error = _hs_open_stream(
                self.database._database,
                c_uint(0),
                byref(stream)
            )
        _assert_success(error)
        self._stream = stream

    def _close_stream(self) -> None:
        if self._stream is None:
            return
        error = _hs_close_stream(
                self._stream,
                self.scratch._scratch,
                self._callback,
                c_void_p()
            )
        _assert_success(error)
        self._stream = None

    def scan(
                self,
                data: Union[bytes, str]
            ) -> None:
        data = self._encode_data(data)
        error = _hs_scan_stream(
                self._stream,
                c_char_p(data),
                c_uint(len(data)),
                c_uint(0),
                self.scratch._scratch,
                self._callback,
                c_void_p()
            )
        _assert_success(error)

    def reset(self) -> None:
        if self._stream is None:
            self._open_stream()
        error = _hs_reset_stream(
                self._stream,
                c_uint(0),
                self.scratch._scratch,
                self._callback,
                c_void_p()
            )
        _assert_success(error)

    def __del__(self) -> None:
        self._close_stream()


class VectorscanCpuFeatures(IntFlag):
    NONE = 0
    AVX2 = 4
    AVX512 = 8
    AVX512VBMI = 16


class VectorscanTuneFamily(IntEnum):
    GENERIC = 0
    SNB = 1
    IVB = 2
    HSW = 3
    SLM = 4
    BDW = 5
    SKL = 6
    SKX = 7
    GLM = 8
    ICL = 9
    ICX = 10


class VectorscanPlatformInfo:

    def __init__(
                self,
                cpu_features: VectorscanCpuFeatures,
                tune_family: VectorscanTuneFamily
            ):
        self._platform_info = _StructHsPlatformInfo(
                c_uint(tune_family.value),
                c_ulonglong(cpu_features.value)
            )


def vectorscan_compile(
            patterns: Dict[int, str],
            mode: VectorscanMode = VectorscanMode.BLOCK,
            flags: VectorscanFlags = VectorscanFlags.NONE,
            platform_info: Optional[VectorscanPlatformInfo] = None
        ) -> VectorscanDatabase:
    database = _hs_database_p()
    compiler_error = _hs_compile_error_p()
    ids = [c_uint(id) for id in patterns.keys()]
    ids = (c_uint * len(ids))(*ids)
    expressions = [
            c_char_p(expression.encode('utf-8')) for expression
            in patterns.values()
        ]
    expressions = (c_char_p * len(expressions))(*expressions)
    c_flags = (c_uint * len(ids))()
    for i in range(0, len(ids)):
        c_flags[i] = c_uint(flags)
    signals.reset()
    platform_info_p = _hs_platform_info_p() if platform_info is None \
        else byref(platform_info._platform_info)
    error = _hs_compile_multi(
            expressions,
            c_flags,
            ids,
            c_uint(len(patterns)),
            c_uint(mode),
            platform_info_p,
            byref(database),
            byref(compiler_error)
        )
    signals.restore()
    _assert_compilation_success(error, compiler_error)
    return VectorscanDatabase(database)


def vectorscan_deserialize(data: bytes) -> VectorscanDatabase:
    _database = _hs_database_p()
    error = _hs_deserialize_database(
            c_char_p(data),
            c_size_t(len(data)),
            byref(_database)
        )
    _assert_success(error)
    return VectorscanDatabase(_database)
