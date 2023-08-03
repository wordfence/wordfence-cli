import os
import json
import pickle

from typing import Any, Callable


class CacheException(BaseException):
    pass


class NoCachedValueException(CacheException):
    pass


class Cache:

    def _serialize_value(self, value: Any) -> Any:
        return value

    def _deserialize_value(self, value: Any) -> Any:
        return value

    def _save(self, key: str, value: str) -> None:
        raise NotImplementedError('Saving is not implemented for this cache')

    def _load(self, key: str) -> str:
        raise NotImplementedError('Loading is not implemented for this cache')

    def put(self, key: str, value) -> None:
        self._save(key, self._serialize_value(value))

    def get(self, key: str) -> Any:
        return self._deserialize_value(self._load(key))


class RuntimeCache(Cache):

    def __init__(self):
        self.items = {}

    def _save(self, key: str, value: Any) -> None:
        self.items[key] = value

    def _load(self, key: str) -> Any:
        if key in self.items:
            return self.items[key]
        raise NoCachedValueException()


# TODO: Implement caching
class CacheDirectory(Cache):

    def __init__(self, path: str):
        self.path = path
        os.makedirs(self.path, mode=0o700, exist_ok=True)

    def _serialize_value(self, value: Any) -> Any:
        return pickle.dumps(value)

    def _deserialize_value(self, value: Any) -> Any:
        return pickle.loads(value)

    def _save(self, key: str, value: Any) -> None:
        pass

    def _load(self, key: str) -> Any:
        raise NoCachedValueException()


class Cacheable:

    def __init__(self, key: str, initializer: Callable[[], Any]):
        self.key = key
        self._initializer = initializer

    def _initialize_value(self) -> Any:
        return self._initializer()

    def get(self, cache: Cache) -> Any:
        try:
            value = cache.get(self.key)
        except NoCachedValueException:
            value = self._initialize_value()
            cache.put(self.key, value)
        return value
