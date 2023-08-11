from .exceptions import ApiException


LICENSE_URL = 'https://www.wordfence.com/products/wordfence-cli/'


class License:

    def __init__(self, key: str):
        self.key = key


class LicenseRequiredException(ApiException):
    pass
