from .exceptions import ApiException


LICENSE_URL = 'https://www.wordfence.com/products/wordfence-cli/'


class License:

    def __init__(self, key: str):
        self.key = key

    def __eq__(self, other):
        return other.key == self.key


class LicenseRequiredException(ApiException):

    def __init__(self):
        super().__init__(
                'License required',
                'A valid Wordfence CLI license is required'
            )


class LicenseSpecific:

    def __init__(self, license: License):
        self.license = license

    def is_compatible_with_license(self, license: License):
        return self.license == license
