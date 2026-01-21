import os
import pickle
import base64
import time
import shutil
from datetime import datetime
from typing import Any, Callable, Optional, Set, Iterable, Tuple

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

    def _save(self, key: str, value: Any) -> int:
        raise NotImplementedError('Saving is not implemented for this cache')

    def _load(self, key: str, max_age: Optional[int]) -> Tuple[Any, int]:
        raise NotImplementedError('Loading is not implemented for this cache')

    def put(self, key: str, value) -> int:
        timestamp = self._save(key, self._serialize_value(value))
        return time.time() - timestamp

    def get_with_age(
                self,
                key: str,
                max_age: Optional[int] = None,
                additional_filters: Optional[Iterable[CacheFilter]] = None
            ) -> Tuple[Any, Optional[int]]:
        value, age = self._load(key, max_age)
        value = self.filter_value(
                self._deserialize_value(value),
                additional_filters
            )
        return value, age

    def get(
                self,
                key: str,
                max_age: Optional[int] = None,
                additional_filters: Optional[Iterable[CacheFilter]] = None
            ) -> Any:
        value, _ = self.get_with_age(key, max_age, additional_filters)
        return value

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

    def _save(self, key: str, value: Any) -> int:
        timestamp = time.time()
        self.items[key] = {
                'value': value,
                'timestamp': timestamp
            }
        return timestamp

    def _load(self, key: str, max_age: Optional[int]) -> Tuple[Any, int]:
        if key in self.items:
            item = self.items[key]
            age = time.time() - item['timestamp']
            if max_age is None or age < max_age:
                return item['value'], age
            else:
                self.remove(key)
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

    def _save(self, key: str, value: Any) -> int:
        path = self._get_path(key)
        with open(path, 'wb') as file:
            with FileLock(file, LockType.EXCLUSIVE):
                file.write(value)
            return os.path.getmtime(path)

    def _get_age(self, path: str) -> int:
        modified_timestamp = os.path.getmtime(path)
        current_timestamp = time.time()
        return current_timestamp - modified_timestamp

    def _is_valid(self, age: int, max_age: Optional[int]) -> bool:
        return max_age is None or age < max_age
        if max_age is None:
            return True

    def _load(self, key: str, max_age: Optional[int]) -> Any:
        path = self._get_path(key)
        try:
            with open(path, 'rb') as file:
                with FileLock(file, LockType.SHARED):
                    age = self._get_age(path)
                    if not self._is_valid(age, max_age):
                        os.remove(path)
                        raise NoCachedValueException()
                    value = file.read()
            return value, age
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


class CacheMessenger:

    def remaining_age(self, age: int, max_age: int) -> int:
        return max_age - age

    def age_to_timestamp(self, age: int, future: bool = False) -> datetime:
        if future:
            age = -age
        timestamp = time.time() - age
        return datetime.fromtimestamp(timestamp)

    def age_to_human_readable_timestamp(
                self,
                age: int,
                future: bool = False
            ) -> str:
        dt = self.age_to_timestamp(age, future)
        return dt.strftime("%x %X")

    def max_age_to_human_readable_timestamp(
                self,
                age: int,
                max_age: int
            ) -> str:
        age = self.remaining_age(age, max_age)
        return self.age_to_human_readable_timestamp(age, True)

    def ages_to_human_readable_timestamps(
                self,
                age: int,
                max_age: int
            ) -> Tuple[str, str]:
        previous = self.age_to_human_readable_timestamp(age)
        next = self.max_age_to_human_readable_timestamp(age, max_age)
        return previous, next

    def invoke_with_timestamps(
                self,
                age: Optional[int],
                max_age: Optional[int],
                cached: bool,
                callback: Callable[[str, str, bool], None],
            ):
        if age is not None and max_age is not None:
            previous, next = \
                    self.ages_to_human_readable_timestamps(age, max_age)
            callback(previous, next, cached)

    def handle_cached(
                self,
                age: Optional[int],
                max_age: Optional[int]
            ) -> None:
        pass

    def handle_updated(
                self,
                age: Optional[int],
                max_age: Optional[int]
            ) -> None:
        pass

    def handle_event(
                self,
                age: Optional[int],
                max_age: Optional[int],
                cached: bool
            ) -> None:
        pass

    def trigger_event(
                self,
                age: Optional[int],
                max_age: Optional[int],
                cached: bool
            ) -> None:
        self.handle_event(age, max_age, cached)
        self.invoke_with_timestamps(age, max_age, cached, self.log_event)
        if cached:
            self.handle_cached(age, max_age)
        else:
            self.handle_updated(age, max_age)

    def log_event(self, previous: str, next: str, cached: bool) -> None:
        pass


class Cacheable:

    def __init__(
                self,
                key: str,
                initializer: Callable[[], Any],
                max_age: Optional[int] = None,
                filters: Optional[Iterable[CacheFilter]] = None,
                messenger: Optional[CacheMessenger] = None
            ):
        self.key = key
        self._initializer = initializer
        self.max_age = max_age
        self.filters = filters
        self.messenger = messenger

    def _initialize_value(self) -> Any:
        return self._initializer()

    def get(self, cache: Cache) -> Any:
        try:
            value, age = cache.get_with_age(
                    self.key,
                    self.max_age,
                    self.filters
                )
            if self.messenger is not None:
                self.messenger.trigger_event(age, self.max_age, True)
        except (
                NoCachedValueException,
                InvalidCachedValueException
                ):
            value = self._initialize_value()
            age = self.set(cache, value)
            if self.messenger is not None:
                self.messenger.trigger_event(age, self.max_age, False)
        return value

    def set(self, cache: Cache, value: Any) -> int:
        return cache.put(self.key, value)

    def delete(self, cache: Cache) -> Any:
        cache.remove(self.key)
