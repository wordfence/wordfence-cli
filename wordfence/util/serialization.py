import pickle
from io import BytesIO
from typing import Any, Set, Optional


class ProhibitedTypeException(BaseException):
    pass


class LimitedDeserializer(pickle.Unpickler):

    def __init__(self, data: bytes, allowed: Set[str]):
        super().__init__(BytesIO(data))
        self.allowed = allowed

    def find_class(self, module, name):
        full_name = f'{module}.{name}'
        if full_name in self.allowed:
            return super().find_class(module, name)
        else:
            raise ProhibitedTypeException(f'Global {full_name} is not allowed')


def limited_deserialize(
            data: bytes,
            allowed: Optional[Set[str]] = None
        ) -> Any:
    if allowed is None:
        allowed = set()
    return LimitedDeserializer(data, allowed).load()
