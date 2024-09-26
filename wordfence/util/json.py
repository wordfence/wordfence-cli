import json
from typing import Any
from base64 import b64encode


UNFILTERED_TYPES = {
        bool,
        int,
        float,
        str
    }


def encode_invalid_data(data) -> Any:
    for unfiltered_type in UNFILTERED_TYPES:
        if isinstance(data, unfiltered_type):
            return data
    if isinstance(data, dict):
        filtered = {}
        for key, value in data.items():
            filtered[encode_invalid_data(key)] = encode_invalid_data(value)
        return filtered
    elif isinstance(data, list):
        filtered = []
        for value in data:
            filtered.append(encode_invalid_data(value))
        return filtered
    elif isinstance(data, bytes):
        return b64encode(data).decode('utf-8')
    else:
        try:
            json.dumps(data)
        except Exception:
            return None


# Encode any data that cannot be represented as valid JSON
# prior to attempting to encode data as JSON
def safe_json_encode(data) -> str:
    return json.dumps(encode_invalid_data(data))
