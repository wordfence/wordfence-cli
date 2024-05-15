import fcntl
import os
import errno
from typing import Optional, IO, TextIO, Generator, Iterable, List, Union, \
    Callable, Set
from enum import Enum, IntEnum
from pathlib import Path
from collections import deque


SYMLINK_IO_ERRORS = {
        errno.ENOENT,  # File not found
        errno.ELOOP  # Too many levels of symbolic links
    }


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
                read = os.read(
                        self.stream.fileno(),
                        self.chunk_size
                    ).decode(self.stream.encoding)
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


def pathlib_resolve(path: str) -> Path:
    return Path(path).expanduser().resolve()


# A memory-optimized tree-set implementation for paths
class PathSet:

    def __init__(self):
        self.children = {}

    def _get_components(self, path: str) -> Iterable[str]:
        return split_path(path)

    def add(self, path: str) -> None:
        components = self._get_components(path)
        node = self.children
        for component in components:
            try:
                node = node[component]
            except KeyError:
                child = {}
                node[component] = child
                node = child

    def contains(self, path: str) -> bool:
        components = self._get_components(path)
        node = self.children
        for component in components:
            try:
                node = node[component]
            except KeyError:
                return False
        return True

    def __contains__(self, path) -> bool:
        if not isinstance(path, str):
            return False
        return self.contains(path)


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
        raise IoException(f'Failed to create directory at {path}')
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


class PathType(Enum):
    FILE = 'file',
    DIRECTORY = 'directory',
    LINK = 'link'


def get_path_type(path: str) -> PathType:
    if os.path.islink(path):
        return PathType.LINK
    elif os.path.isdir(path):
        return PathType.DIRECTORY
    else:
        return PathType.FILE


def is_same_file(path: str, other: str) -> bool:
    type = get_path_type(path)
    other_type = get_path_type(other)
    if type is not other_type:
        return False
    return os.path.samefile(path, other)


def is_symlink_error(error: OSError) -> bool:
    return error.errno in SYMLINK_IO_ERRORS


def is_symlink_loop(
            path: str,
            parents: Optional[Union[Iterable[str], PathSet]] = None
        ) -> bool:
    realpath = os.path.realpath(path)
    try:
        if is_same_file(path, realpath):
            return True
    except OSError as error:
        if error.errno == errno.ENOENT:
            return False
        if error.errno == errno.ELOOP:
            return True
        raise
    if parents is not None:
        if isinstance(parents, PathSet):
            if realpath in parents:
                return True
        else:
            for parent in parents:
                if realpath == parent:
                    return True
    return False


def is_symlink_and_loop(
            path: str,
            parents: Optional[Union[Iterable[str], PathSet]] = None
        ) -> bool:
    try:
        if not os.path.islink(path):
            return False
    except OSError:
        return False
    return is_symlink_loop(path, parents)


def get_all_parents(path: str) -> List[str]:
    parents = [path]
    while len(path) > 1:
        path = os.path.dirname(path)
        parents.append(path)
    return parents


def split_path(path: str) -> Iterable[str]:
    components = deque()
    while len(path) > 1:
        components.appendleft(os.path.basename(path))
        path = os.path.dirname(path)
    return components


def populate_parents(
            path: Union[str, os.PathLike],
            parents: Optional[Set[str]] = None
        ) -> Set[str]:
    path = str(path)
    if parents is None:
        parents = set()
    else:
        parents = parents.copy()
    parents.update(get_all_parents(path))
    return parents


def iterate_files(
            path: Union[str, os.PathLike],
            parents: Optional[Set[str]] = None,
            loop_callback: Optional[Callable[[str], None]] = None
        ) -> Generator[str, None, None]:
    parents = populate_parents(path, parents)
    if is_symlink_and_loop(str(path), parents):
        if loop_callback is not None:
            loop_callback(str(path))
        return
    contents = os.scandir(path)
    for item in contents:
        if is_symlink_and_loop(str(item.path), parents):
            if loop_callback is not None:
                loop_callback(str(item.path))
            continue
        if item.is_dir():
            yield from iterate_files(item.path, parents, loop_callback)
        else:
            yield item.path


def get_umask() -> int:
    current = os.umask(0)
    os.umask(current)
    return current


def umask_mode(mode: int) -> int:
    umask = get_umask()
    return mode & ~umask


def chmod_with_umask(path: str, mode: int = 0o666) -> int:
    mode = umask_mode(mode)
    os.chmod(path, mode)
