from typing import Optional, Union

from ..api.licensing import License, LicenseSpecific, to_license
from ..api.exceptions import ApiException
from ..api import noc1
from ..util.caching import NoCachedValueException, InvalidCachedValueException
from .context import CliContext


CACHE_KEY = 'license'
CACHEABLE_TYPES = {
        'wordfence.api.licensing.LicenseSpecific'
    }


class LicenseValidationFailure(Exception):

    def __init__(self, message: str):  # noqa: B042
        self.message = message


class LicenseManager:

    def __init__(self, context: CliContext):
        self.context = context

    def _create_noc1_client(
                self,
                license: Optional[License] = None
            ) -> noc1.Client:
        return self.context.create_noc1_client(license)

    def request_free_license(self, terms_accepted: bool = False) -> License:
        client = self.context.create_noc1_client()
        return License(client.get_cli_api_key(accept_terms=terms_accepted))

    def validate_license(self, license: Union[License, str]) -> License:
        license = to_license(license)
        client = self.context.create_noc1_client(license)
        try:
            if not client.ping_api_key():
                raise LicenseValidationFailure('Invalid license')
        except ApiException as exception:
            if exception.public_message is None:
                raise LicenseValidationFailure(
                        'License validation failed.'
                    )
            else:
                raise LicenseValidationFailure(
                        f'Invalid license: {exception.public_message}'
                    )
        return license

    def set_license(self, license: Union[License, str]) -> str:
        license = to_license(license)
        self.context.cache.put(CACHE_KEY, LicenseSpecific(license))

    def check_license(self) -> License:
        current = self.context.get_license()
        try:
            cached = self.context.cache.get(CACHE_KEY)
            if cached.is_compatible_with_license(current):
                return cached.license
        except NoCachedValueException:
            pass
        except InvalidCachedValueException:
            pass
        self.validate_license(current)
        self.set_license(current)
        return current

    def update_license(self, license: License) -> None:
        self.set_license(license)
