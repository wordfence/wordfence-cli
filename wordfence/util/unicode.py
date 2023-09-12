import unicodedata


def filter_control_characters(string: str) -> str:
    return "".join(
            ch for ch in string if unicodedata.category(ch)[0] != "C"
        )
