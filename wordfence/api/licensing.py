from .exceptions import ApiException


class License:

    def __init__(self, key: str):
        self.key = key


class LicenseRequiredException(ApiException):
    pass
