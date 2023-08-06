import os
import pickle
import base64
import time
from typing import Any, Callable, Optional, Set

from .io import FileLock, LockType
from .serialization import limited_deserialize


class CacheException(BaseException):
    pass


class NoCachedValueException(CacheException):
    pass


class Cache:

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

    def get(self, key: str, max_age: Optional[int] = None) -> Any:
        return self._deserialize_value(self._load(key, max_age))


class RuntimeCache(Cache):

    def __init__(self):
        self.items = {}

    def _save(self, key: str, value: Any) -> None:
        self.items[key] = value

    def _load(self, key: str, max_age: Optional[int]) -> Any:
        if key in self.items:
            return self.items[key]
        raise NoCachedValueException()


# TODO: Implement caching
class CacheDirectory(Cache):

    def __init__(self, path: str, allowed: Optional[Set[str]] = None):
        self.path = path
        self.allowed = allowed
        os.makedirs(self.path, mode=0o700, exist_ok=True)

    def _serialize_value(self, value: Any) -> Any:
        return pickle.dumps(value)

    def _deserialize_value(self, value: Any) -> Any:
        # return pickle.loads(value)
        return limited_deserialize(value, self.allowed)

    def _get_path(self, key: str) -> str:
        return os.path.join(
                self.path,
                base64.b16encode(key.encode('utf-8')).decode('utf-8')
            )

    def _save(self, key: str, value: Any) -> None:
        path = self._get_path(key)
        with open(path, 'xb') as file:
            with FileLock(file, LockType.EXCLUSIVE):
                file.write(value)

    def _is_valid(self, path: str, max_age: Optional[int]) -> bool:
        if max_age is None:
            return True
        modified_timestamp = os.path.getmtime(path)
        current_timestamp = time.time()
        return current_timestamp - modified_timestamp < max_age

    def _load(self, key: str, max_age: Optional[int]) -> Any:
        # TODO: Delete old cached data
        path = self._get_path(key)
        try:
            with open(path, 'rb') as file:
                with FileLock(file, LockType.SHARED):
                    if not self._is_valid(path, max_age):
                        os.remove(path)
                        raise NoCachedValueException()
                    value = file.read()
            return value
        except FileNotFoundError:
            raise NoCachedValueException()


class Cacheable:

    def __init__(
                self,
                key: str,
                initializer: Callable[[], Any],
                max_age: Optional[int] = None
            ):
        self.key = key
        self._initializer = initializer
        self.max_age = max_age

    def _initialize_value(self) -> Any:
        return self._initializer()

    def get(self, cache: Cache) -> Any:
        try:
            value = cache.get(self.key, self.max_age)
        except NoCachedValueException:
            value = self._initialize_value()
            cache.put(self.key, value)
        return value