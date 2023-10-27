import re
from dataclasses import dataclass
from enum import Enum

KIBIBYTE = 1024
MEBIBYTE = 1024 * 1024

sizings_map = {
    'b': 1,
    'k': KIBIBYTE,
    'kb': KIBIBYTE,
    'kib': KIBIBYTE,
    'm': MEBIBYTE,
    'mb': MEBIBYTE,
    'mib': MEBIBYTE
}
"""maps suffixes to byte multipliers; k/kb/kib are synonyms, as are m/mb/mib"""


def byte_length(conversion_value: str) -> int:
    match = re.search(r"(\d+)([^0-9].*)", conversion_value)
    if not match:
        raise ValueError("Invalid format for byte length type")
    suffix = match.group(2).lower()
    if not sizings_map.get(suffix, False):
        raise ValueError("Unrecognized byte length suffix")
    return int(match.group(1)) * sizings_map.get(suffix)


class ByteUnit(Enum):
    BYTE = (1, 'B')
    KIBIBYTE = (pow(2, 10), 'KiB')
    MEBIBYTE = (pow(2, 20), 'MiB')
    GIBIBYTE = (pow(2, 30), 'GiB')
    TEBIBYTE = (pow(2, 40), 'TiB')

    def __init__(
                self,
                size: int,
                abbreviation: str
            ):
        self.size = size
        self.abbreviation = abbreviation


@dataclass
class ByteUnitValue:
    value: float
    unit: ByteUnit

    def __str__(self) -> str:
        if self.unit.size == 1:
            value = int(self.value)
        else:
            value = round(self.value, 1)
        return f'{value} {self.unit.abbreviation}'


def scale_byte_unit(byte_count: int) -> ByteUnitValue:
    scaled_unit = ByteUnit.BYTE
    for unit in ByteUnit:
        if byte_count >= unit.size \
                and (
                    scaled_unit is None
                    or unit.size > scaled_unit.size
                ):
            scaled_unit = unit
    scaled_value = byte_count / scaled_unit.size
    return ByteUnitValue(scaled_value, scaled_unit)
