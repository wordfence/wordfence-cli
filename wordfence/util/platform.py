from enum import Enum
from platform import machine
from typing import Optional, Set


class Platform(Enum):

    AMD64 = ('amd64', {'amd64'})
    ARM64 = ('arm64', {'x86_64'})

    def __init__(self, key: str, machine_names: Set[str]):
        self.key = key
        self.machine_names = machine_names

    @classmethod
    def detect(cls) -> Optional:
        machine_name = machine()
        for platform in cls:
            if machine_name in platform.machine_names:
                return platform
        return None
