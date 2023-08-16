from ..api.licensing import License, LicenseSpecific


class CommonString:

    def __init__(self, string: str, signature_ids: list = None):
        self.string = string
        if signature_ids is None:
            signature_ids = []
        self.signature_ids = signature_ids


class Signature:

    def __init__(
                self,
                identifier: int,
                rule: str,
                name: str,
                description: str,
                common_strings: list = None
            ):
        self.identifier = identifier
        self.rule = rule
        self.name = name
        self.description = description
        self.common_strings = common_strings \
            if common_strings is not None \
            else []

    def get_common_string_count(self) -> int:
        return len(self.common_strings)

    def has_common_strings(self) -> bool:
        return self.get_common_string_count() > 0


class SignatureSet(LicenseSpecific):

    def __init__(
                self,
                common_strings: list,
                signatures: dict,
                license: License = None
            ):
        super().__init__(license)
        self.common_strings = common_strings
        self.signatures = signatures

    def remove_signature(self, identifier: int) -> bool:
        if identifier not in self.signatures:
            return False
        signature = self.signatures[identifier]
        for index in signature.common_strings:
            self.common_strings[index].signature_ids.remove(identifier)
        del self.signatures[identifier]
        return True

    def get_signature(self, identifier: int) -> None:
        if identifier in self.signatures:
            return self.signatures[identifier]
        raise ValueError(f'Invalid signature identifier: {identifier}')
