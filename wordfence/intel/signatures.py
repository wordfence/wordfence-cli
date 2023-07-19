class CommonString:

    def __init__(self, string: str, signature_ids: list = None):
        self.string = string
        if signature_ids is None:
            signature_ids = []
        self.signature_ids = signature_ids


class Signature:

    def __init__(self, identifier: int, rule: str, common_strings: list = []):
        self.identifier = identifier
        self.rule = rule
        self.common_strings = common_strings

    def get_common_string_count(self) -> int:
        return len(self.common_strings)

    def has_common_strings(self) -> bool:
        return self.get_common_string_count() > 0


class SignatureSet:

    def __init__(self, common_strings: list, signatures: dict):
        self.common_strings = common_strings
        self.signatures = signatures
