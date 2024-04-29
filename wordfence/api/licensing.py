from typing import Union, Optional

from .exceptions import ApiException


LICENSE_URL = 'https://www.wordfence.com/products/wordfence-cli/'


class License:

    def __init__(self, key: str):
        self.key = key
        self.paid = False

    def __eq__(self, other):
        return other.key == self.key

    def __str__(self) -> str:
        return self.key


def to_license(license: Union[License, str]) -> License:
    if isinstance(license, License):
        return license
    return License(license)


class LicenseRequiredException(ApiException):

    def __init__(self):
        super().__init__(
                'License required',
                'A valid Wordfence CLI license is required'
            )


class LicenseSpecific:

    def __init__(self, license: Optional[License]):
        self.license = license

    def is_compatible_with_license(self, license: License):
        return self.license is None or self.license == license

    def assign_license(self, license: Optional[License]):
        self.license = license

    def clear_license(self):
        self.assign_license(None)
