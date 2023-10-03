import re

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
