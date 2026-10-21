import fcntl
import os
from typing import Optional, IO, TextIO, Generator, List, Set
from enum import IntEnum


PRODUCTION_PATH = '/www'
STAGING_PATH = '/staging'


def resolve_staging_paths() -> Set[str]:
    """Every path that leads to the Flywheel staging site at /staging.

    Resolving these once lets a directory walk recognize the staging site
    without calling realpath() on everything it visits.
    """
    paths = {STAGING_PATH}
    try:
        paths.add(os.path.realpath(STAGING_PATH))
    except OSError:
        pass
    return paths


def is_staging_path(path: str) -> bool:
    """Whether a path refers to the Flywheel staging site at /staging."""
    if path == STAGING_PATH:
        return True
    try:
        return os.path.realpath(path) in resolve_staging_paths()
    except OSError:
        return False


def get_site_paths(include_staging: bool = False) -> List[str]:
    """The Flywheel site directories that should be scanned."""
    if include_staging:
        return [PRODUCTION_PATH, STAGING_PATH]
    return [PRODUCTION_PATH]


class IoException(Exception):
    pass


class StreamReader:

    def __init__(self, stream: TextIO, delimiter: str, chunk_size: int = 1024):
        self.stream = stream
        self.delimiter = delimiter
        self.chunk_size = chunk_size
        self._buffer = ''
        self._end_of_stream = False

    def read_entry(self) -> Optional[str]:
        while True:
            index = self._buffer.find(self.delimiter)
            if index != -1:
                entry = self._buffer[:index]
                self._buffer = self._buffer[index + 1:]
                return entry
            elif not self._end_of_stream:
                read = self.stream.read(self.chunk_size)
                if read == '':
                    self._end_of_stream = True
                self._buffer += read
            else:
                break
        if len(self._buffer) > 0:
            path = self._buffer
            self._buffer = ''
            return path
        else:
            return None

    def read_all_entries(self) -> Generator[str, None, None]:
        while (entry := self.read_entry()) is not None:
            yield entry


class LockType(IntEnum):
    EXCLUSIVE = fcntl.LOCK_EX
    SHARED = fcntl.LOCK_SH


class FileLock:

    def __init__(self, file: IO, lock_type: LockType = LockType.EXCLUSIVE):
        self.file = file
        self.lock_type = lock_type

    def _operate_lock(self, action: int):
        fcntl.flock(self.file, action)

    def __enter__(self):
        self._operate_lock(self.lock_type.value)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._operate_lock(fcntl.LOCK_UN)


def resolve_path(path: str) -> str:
    """ Resolve a path to a normalized, absolute path """
    return os.path.abspath(os.path.expanduser(path))


DEFAULT_CREATE_MODE = 0o700


def ensure_directory_is_writable(
            path: str,
            create_mode: int = DEFAULT_CREATE_MODE
        ) -> str:
    """ Ensure that the specified directory is writable, """
    """ creating it and parent directories as needed. Note """
    """ that the checks here are not atomic; this assumes """
    """ that nothing else is modifying the filesystem which """
    """ is not guaranteed. """
    path = resolve_path(path)
    if os.path.exists(path):
        if os.path.isdir(path):
            if not os.access(path, os.W_OK):
                raise IoException(f'Directory at {path} is not writable')
            if not os.access(path, os.X_OK):
                raise IoException(f'Directory at {path} is not executable')
            return path
        else:
            raise IoException(f'Path {path} exists and is not a directory')
    try:
        os.makedirs(path, mode=create_mode, exist_ok=True)
    except OSError:
        raise IoException('Failed to create directory at {$path}')
    return path


def ensure_file_is_writable(
            path: str,
            create_mode: int = 0o700
        ) -> str:
    path = resolve_path(path)
    if os.path.exists(path):
        if not os.path.isfile(path):
            raise IoException(f'Path {path} already exists, but is not a file')
        if not os.access(path, os.W_OK):
            raise IoException(f'File at {path} is not writable')
        return path
    else:
        return ensure_directory_is_writable(os.path.dirname(path))
