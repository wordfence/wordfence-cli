from typing import Optional


def bytes_to_str(value: Optional[bytes]) -> Optional[str]:
    if value is None:
        return None
    return value.decode('latin1', 'replace')


def str_to_bytes(value: Optional[str]) -> Optional[bytes]:
    if value is None:
        return None
    return value.encode('latin1', 'replace')


def force_encoding(encoding: str, value: str) -> str:
    return value.encode(encoding, errors="replace").decode(encoding)
