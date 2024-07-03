import os
import pickle
import base64
import time
import shutil
from typing import Any, Callable, Optional, Set, Iterable

from .io import FileLock, LockType
from .serialization import limited_deserialize
from ..logging import log


DURATION_ONE_DAY = 86400


class CacheException(Exception):
    pass


class NoCachedValueException(CacheException):
    pass


class InvalidCachedValueException(CacheException):
    pass


CacheFilter = Callable[[Any], Any]


class Cache:

    def __init__(self):
        self.filters = []

    def _serialize_value(self, value: Any) -> Any:
        return value

    def _deserialize_value(self, value: Any) -> Any:
        return value

    def _save(self, key: str, value: Any) -> None:
        raise NotImplementedError('Saving is not implemented for this cache')

    def _load(self, key: str, max_age: Optional[int]) -> Any:
        raise NotImplementedError('Loading is not implemented for this cache')

    def put(self, key: str, value) -> None:
        self._save(key, self._serialize_value(value))

    def get(
                self,
                key: str,
                max_age: Optional[int] = None,
                additional_filters: Optional[Iterable[CacheFilter]] = None
            ) -> Any:
        return self.filter_value(
                self._deserialize_value(self._load(key, max_age)),
                additional_filters
            )

    def remove(self, key: str) -> None:
        raise NotImplementedError('Removing is not implemented for this cache')

    def purge(self) -> None:
        pass

    def add_filter(self, filter: CacheFilter) -> None:
        self.filters.append(filter)

    def filter_value(
                self,
                value: Any,
                additional_filters: Optional[Iterable[CacheFilter]] = None
            ) -> Any:
        for filter in self.filters:
            value = filter(value)
        if additional_filters is not None:
            for filter in additional_filters:
                value = filter(value)
        return value


class RuntimeCache(Cache):

    def __init__(self):
        super().__init__()
        self.purge()

    def _save(self, key: str, value: Any) -> None:
        self.items[key] = value

    def _load(self, key: str, max_age: Optional[int]) -> Any:
        if key in self.items:
            return self.items[key]
        raise NoCachedValueException()

    def remove(self, key: str) -> None:
        try:
            del self.items[key]
        except KeyError:
            # The item already does not exist
            pass

    def purge(self) -> None:
        self.items = {}


class CacheDirectory(Cache):

    def __init__(self, path: bytes, allowed: Optional[Set[str]] = None):
        super().__init__()
        self.path = path
        self.allowed = allowed
        self._initialize_directory()

    def _initialize_directory(self) -> None:
        try:
            os.makedirs(self.path, mode=0o700, exist_ok=True)
        except OSError as e:
            raise CacheException(
                    f'Failed to initialize cache directory at {self.path}'
                ) from e

    def _serialize_value(self, value: Any) -> Any:
        return pickle.dumps(value)

    def _deserialize_value(self, value: Any) -> Any:
        return limited_deserialize(value, self.allowed)

    def _get_path(self, key: str) -> bytes:
        return os.path.join(
                self.path,
                os.fsencode(base64.b16encode(key.encode('utf-8')))
            )

    def _save(self, key: str, value: Any) -> None:
        path = self._get_path(key)
        with open(path, 'wb') as file:
            with FileLock(file, LockType.EXCLUSIVE):
                file.write(value)

    def _is_valid(self, path: str, max_age: Optional[int]) -> bool:
        if max_age is None:
            return True
        modified_timestamp = os.path.getmtime(path)
        current_timestamp = time.time()
        return current_timestamp - modified_timestamp < max_age

    def _load(self, key: str, max_age: Optional[int]) -> Any:
        path = self._get_path(key)
        try:
            with open(path, 'rb') as file:
                with FileLock(file, LockType.SHARED):
                    if not self._is_valid(path, max_age):
                        os.remove(path)
                        raise NoCachedValueException()
                    value = file.read()
            return value
        except OSError as e:
            if not isinstance(e, FileNotFoundError):
                log.warning(
                        'Unexpected error occurred while reading from cache: '
                        + str(e)
                    )
            raise NoCachedValueException() from e

    def remove(self, key: str) -> None:
        path = self._get_path(key)
        with open(path, 'wb') as file:
            with FileLock(file, LockType.EXCLUSIVE):
                os.remove(path)

    def purge(self) -> None:
        try:
            shutil.rmtree(self.path)
        except BaseException as e:  # noqa: B036
            raise CacheException('Failed to delete cache directory') from e
        self._initialize_directory()


class Cacheable:

    def __init__(
                self,
                key: str,
                initializer: Callable[[], Any],
                max_age: Optional[int] = None,
                filters: Optional[Iterable[CacheFilter]] = None
            ):
        self.key = key
        self._initializer = initializer
        self.max_age = max_age
        self.filters = filters

    def _initialize_value(self) -> Any:
        return self._initializer()

    def get(self, cache: Cache) -> Any:
        try:
            value = cache.get(self.key, self.max_age, self.filters)
        except (
                NoCachedValueException,
                InvalidCachedValueException
                ):
            value = self._initialize_value()
            self.set(cache, value)
        return value

    def set(self, cache: Cache, value: Any) -> None:
        cache.put(self.key, value)

    def delete(self, cache: Cache) -> Any:
        cache.remove(self.key)
