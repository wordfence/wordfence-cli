import fcntl
import os
import errno
from typing import Optional, IO, TextIO, Generator, Iterable, List, Union, \
    Callable, Set, BinaryIO
from enum import Enum, IntEnum
from collections import deque


SYMLINK_IO_ERRORS = {
        errno.ENOENT,  # File not found
        errno.ELOOP  # Too many levels of symbolic links
    }


class IoException(Exception):
    pass


class StreamReader:

    def __init__(
                self,
                stream: Union[TextIO, BinaryIO],
                delimiter: Union[str, bytes],
                chunk_size: int = 1024,
                binary: bool = False
            ):
        self.stream = stream
        self.delimiter = delimiter
        self.chunk_size = chunk_size
        self.binary = binary
        self._initialize_buffer()
        self._end_of_stream = False
        self._empty = self._initialize_empty_string()

    def _initialize_empty_string(self) -> Union[str, bytes]:
        return b'' if self.binary else ''

    def _initialize_buffer(self) -> None:
        self._buffer = self._initialize_empty_string()

    def read_entry(self) -> Optional[Union[str, bytes]]:
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
                    )
                if not self.binary:
                    read = read.decode(self.stream.encoding)
                if read == self._empty:
                    self._end_of_stream = True
                self._buffer += read
            else:
                break
        if len(self._buffer) > 0:
            path = self._buffer
            self._initialize_buffer()
            return path
        else:
            return None

    def read_all_entries(self) -> Generator[Union[str, bytes], None, None]:
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


def resolve_path(path: bytes) -> bytes:
    """ Resolve a path to a normalized, absolute path """
    return os.path.abspath(os.path.expanduser(path))


def resolve_parent_path(path: bytes) -> bytes:
    return resolve_path(os.path.dirname(path))


def get_path_components(path: bytes) -> bytes:
    components = []
    while len(path) > 0:
        path, current = os.path.split(path)
        if len(current) > 0:
            components.append(current)
        else:
            break
    components.reverse()
    return components


# A memory-optimized tree-set implementation for paths
class PathSet:

    def __init__(self):
        self.children = {}

    def _get_components(self, path: bytes) -> Iterable[bytes]:
        return split_path(path)

    def add(self, path: bytes) -> None:
        components = self._get_components(path)
        node = self.children
        for component in components:
            try:
                node = node[component]
            except KeyError:
                child = {}
                node[component] = child
                node = child

    def contains(self, path: bytes) -> bool:
        components = self._get_components(path)
        node = self.children
        for component in components:
            try:
                node = node[component]
            except KeyError:
                return False
        return True

    def __contains__(self, path) -> bool:
        if not isinstance(path, bytes):
            return False
        return self.contains(path)


DEFAULT_CREATE_MODE = 0o700


def ensure_directory_is_writable(
            path: bytes,
            create_mode: int = DEFAULT_CREATE_MODE
        ) -> bytes:
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
            path: bytes,
            create_mode: int = 0o700
        ) -> bytes:
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


def get_path_type(path: bytes) -> PathType:
    if os.path.islink(path):
        return PathType.LINK
    elif os.path.isdir(path):
        return PathType.DIRECTORY
    else:
        return PathType.FILE


def is_same_file(path: bytes, other: bytes) -> bool:
    type = get_path_type(path)
    other_type = get_path_type(other)
    if type is not other_type:
        return False
    return os.path.samefile(path, other)


def is_symlink_error(error: OSError) -> bool:
    return error.errno in SYMLINK_IO_ERRORS


def is_symlink_loop(
            path: bytes,
            parents: Optional[Union[Iterable[bytes], PathSet]] = None
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
            path: bytes,
            parents: Optional[Union[Iterable[bytes], PathSet]] = None
        ) -> bool:
    try:
        if not os.path.islink(path):
            return False
    except OSError:
        return False
    return is_symlink_loop(path, parents)


def get_all_parents(path: bytes) -> List[bytes]:
    parents = [path]
    while len(path) > 1:
        path = os.path.dirname(path)
        parents.append(path)
    return parents


def split_path(path: bytes) -> Iterable[bytes]:
    components = deque()
    while len(path) > 1:
        components.appendleft(os.path.basename(path))
        path = os.path.dirname(path)
    return components


def populate_parents(
            path: bytes,
            parents: Optional[Set[bytes]] = None
        ) -> Set[str]:
    if parents is None:
        parents = set()
    else:
        parents = parents.copy()
    parents.update(get_all_parents(path))
    return parents


def iterate_files(
            path: bytes,
            parents: Optional[Set[bytes]] = None,
            loop_callback: Optional[Callable[[bytes], None]] = None
        ) -> Generator[str, None, None]:
    parents = populate_parents(path, parents)
    if is_symlink_and_loop(path, parents):
        if loop_callback is not None:
            loop_callback(path)
        return
    contents = os.scandir(path)
    for item in contents:
        if is_symlink_and_loop(item.path, parents):
            if loop_callback is not None:
                loop_callback(item.path)
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


def chmod_with_umask(path: bytes, mode: int = 0o666) -> int:
    mode = umask_mode(mode)
    os.chmod(path, mode)


class PathProperties:

    def __init__(self, path: bytes):
        self.path = path
        self.directory, self.basename = os.path.split(self.path)
        self.stem, self.extension = os.path.splitext(self.basename)

    def has_extension(self) -> bool:
        return len(self.extension) > 0
