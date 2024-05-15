from hashlib import sha256
from typing import Optional

from ..api.licensing import License, LicenseSpecific
from ..util.serialization import limited_deserialize


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
                license: Optional[License] = None
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

    def get_signature(self, identifier: int) -> Signature:
        if identifier in self.signatures:
            return self.signatures[identifier]
        raise ValueError(f'Invalid signature identifier: {identifier}')

    def has_signature(self, identifier: int) -> bool:
        try:
            self.get_signature(identifier)
            return True
        except ValueError:
            return False

    def get_hash(self) -> str:
        hash = sha256()
        delimiter = ';'
        for signature in self.signatures.values():
            hash.update(delimiter.join([
                    str(signature.identifier),
                    signature.rule,
                    delimiter.join(
                            [self.common_strings[index].string for index
                                in signature.common_strings]
                        )
                ]).encode('utf-8'))
        return hash.digest()


class PrecompiledSignatureSet(LicenseSpecific):

    VERSION = 1

    def __init__(
                self,
                signature_set: SignatureSet,
                data: bytes,
                signature_hash: Optional[bytes] = None,
                license: Optional[License] = None
            ):
        super().__init__(license)
        self.signature_set = signature_set
        self.signature_hash = (
                signature_set if isinstance(signature_set, bytes)
                else signature_set.get_hash()
            )
        self.data = data
        self.version = self.VERSION

    def is_supported_version(self) -> bool:
        return hasattr(self, 'version') and self.version == self.VERSION

    def assign_license(self, license: Optional[License]):
        super().assign_license(license)
        self.signature_set.assign_license(license)


def deserialize_precompiled_signature_set(data):
    signature_set = limited_deserialize(
            data,
            {
                'wordfence.api.licensing.License',
                'wordfence.intel.signatures.PrecompiledSignatureSet',
                'wordfence.intel.signatures.SignatureSet',
                'wordfence.intel.signatures.Signature',
                'wordfence.intel.signatures.CommonString'
            },
            PrecompiledSignatureSet
        )
    return signature_set
